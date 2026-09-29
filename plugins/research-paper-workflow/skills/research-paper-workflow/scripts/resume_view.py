#!/usr/bin/env python3
"""Read-only, rebuildable projection of explicitly mapped existing project notes.

No source migration, state mutation, commands, claim database, or authorization.
JSON pointers follow RFC 6901. Markdown support is an exact, unique ATX heading
line and its section, quoted without interpreting its prose as structured state.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime as dt
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys


SCHEMA = "research-resume-view.v1"
ADAPTER_SCHEMA = "research-resume-adapter.v1"
LIMIT = ("Derived navigation only; mapped records remain authoritative. This view "
         "does not establish scientific support, task completion, or permission. "
         "Unmapped records and dependency completeness remain unknown.")
FIELDS = {
    "issues": {"id", "status", "summary", "version", "next_action"},
    "decisions": {"id", "status", "summary", "version", "topic", "supersedes"},
    "evidence": {"id", "status", "summary", "version", "path"},
    "artifacts": {"id", "path", "version", "issue_id", "relation", "relation_version"},
}
ORIGIN_FIELDS = {"source_kind", "source_locator"}
for _fields in FIELDS.values():
    _fields.update(ORIGIN_FIELDS)
STATES = {
    "issues": {"active", "pending", "completed", "blocked", "rejected", "deferred", "superseded"},
    "decisions": {"adopted", "pending", "rejected", "deferred", "superseded"},
    "evidence": {"available", "withdrawn", "superseded"},
    "artifacts": {"affected", "unrelated", "unknown"},
}


class ViewError(ValueError):
    pass


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ViewError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ViewError(f"invalid JSON number: {value}")))


def pointer_parts(pointer):
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ViewError("JSON pointer must be empty or start with /")
    if re.search(r"~(?![01])", pointer):
        raise ViewError("invalid JSON pointer escape")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")] if pointer else []


def lookup(value, pointer):
    for part in pointer_parts(pointer):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", part) and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ViewError(f"unresolved JSON pointer: {pointer}")
    return value


def relative(name):
    if (not isinstance(name, str) or not name or "\\" in name
            or PurePosixPath(name).is_absolute()
            or any(part in {"", ".", ".."} for part in name.split("/"))):
        raise ViewError("path must be project-relative without traversal")
    return name


def safe_path(root, name):
    relative(name)
    path = root
    for part in name.split("/"):
        path /= part
        if path.is_symlink():
            raise ViewError(f"symlink source not supported: {name}")
    return path


def read_bytes(root, name):
    path = safe_path(root, name)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ViewError("source is not a regular file")
    return path.read_bytes()


class Reader:
    def __init__(self, root):
        self.root = root
        self.raw = {}
        self.sources = {}

    def read(self, name):
        if name not in self.sources:
            try:
                content = read_bytes(self.root, name)
                self.sources[name] = {"path": name, "sha256": hashlib.sha256(content).hexdigest(), "status": "read"}
                self.raw[name] = content
            except (OSError, ValueError) as exc:
                self.sources[name] = {"path": name, "sha256": None,
                                      "status": "missing" if isinstance(exc, FileNotFoundError) else "unreadable"}
                self.raw[name] = None
        if self.raw[name] is None:
            raise ViewError(f"source {self.sources[name]['status']}: {name}")
        return self.raw[name]

    def source(self, name, pointer=None):
        result = dict(self.sources.get(name, {"path": name, "sha256": None, "status": "unread"}))
        if pointer is not None:
            result["pointer"] = pointer
        return result

    def select(self, ref):
        try:
            value = lookup(parse(self.read(ref["path"])), ref["pointer"])
            return {"status": "known", "value": value, "source": self.source(ref["path"], ref["pointer"])}
        except (OSError, ValueError, UnicodeError) as exc:
            return {"status": "unknown", "value": None, "reason": str(exc),
                    "source": self.source(ref["path"], ref["pointer"])}


def unknown(reason, source=None):
    result = {"status": "unknown", "value": None, "reason": reason}
    if source:
        result["source"] = source
    return result


def validate_ref(ref, extra=()):
    if not isinstance(ref, dict) or set(ref) != {"path", "pointer"} | set(extra):
        raise ViewError("reference needs path/pointer and only its documented mapping fields")
    # Validate lexically without reading any source or executing anything.
    relative(ref["path"])
    pointer_parts(ref["pointer"])


def validate_adapter(adapter):
    allowed = {"schema_version", "objective", "active_version", "quotes", "reports"} | set(FIELDS)
    if not isinstance(adapter, dict) or adapter.get("schema_version") != ADAPTER_SCHEMA or set(adapter) - allowed:
        raise ViewError(f"adapter must be {ADAPTER_SCHEMA}; inline facts and unknown keys are not supported")
    for name in ("objective", "active_version"):
        if name in adapter:
            validate_ref(adapter[name])
    for name, allowed_fields in FIELDS.items():
        if name not in adapter:
            continue
        spec = adapter[name]
        map_key = "relation_map" if name == "artifacts" else "status_map"
        validate_ref(spec, {"fields"} | ({map_key} if isinstance(spec, dict) and map_key in spec else set()))
        fields = spec["fields"]
        if not isinstance(fields, dict) or set(fields) - allowed_fields:
            raise ViewError(f"unsupported {name} fields")
        for pointer in fields.values():
            pointer_parts(pointer)
        if map_key in spec and (not isinstance(spec[map_key], dict)
                                or any(value not in STATES[name] for value in spec[map_key].values())):
            raise ViewError(f"{map_key} maps source strings to documented states only")
    for quote in adapter.get("quotes", []):
        if not isinstance(quote, dict) or set(quote) != {"path", "heading"}:
            raise ViewError("quote requires only path and exact heading")
        relative(quote["path"])
        if not isinstance(quote["heading"], str) or not re.fullmatch(r"#{1,6} [^\n]+", quote["heading"]):
            raise ViewError("quote heading must be the complete ATX heading line")
    for report in adapter.get("reports", []):
        validate_ref(report, {"dependencies"} if isinstance(report, dict) and "dependencies" in report else set())
        if "dependencies" in report:
            dep = report["dependencies"]
            validate_ref(dep, {"fields"})
            if not isinstance(dep["fields"], dict) or set(dep["fields"]) != {"path", "sha256"}:
                raise ViewError("report dependencies map only path and sha256")
            for pointer in dep["fields"].values():
                pointer_parts(pointer)


def scalar(reader, ref):
    result = reader.select(ref) if ref else unknown("adapter mapping is required")
    if result["status"] == "known" and (not isinstance(result["value"], (str, int, float, bool)) or result["value"] == ""):
        return unknown("mapped value must be a nonempty scalar; no prose inference or object copy", result["source"])
    return result


def records(reader, spec, name):
    if spec is None:
        return {"status": "unknown", "reason": "adapter mapping is required", "records": []}
    selected = reader.select(spec)
    if selected["status"] != "known" or not isinstance(selected["value"], list):
        return {"status": "unknown", "reason": selected.get("reason", "mapped collection must be an array"),
                "source": selected["source"], "records": []}
    result = []
    for index, raw in enumerate(selected["value"]):
        base = spec["pointer"] + "/" + str(index)
        record = {"source": reader.source(spec["path"], base), "field_sources": {}, "unknown_fields": {}}
        # path is optional for evidence; absent paths do not invent evidence files.
        names = FIELDS[name] - ({"path"} if name == "evidence" and "path" not in spec["fields"] else set())
        if name == "artifacts" and "relation_version" not in spec["fields"]:
            names = names - {"relation_version"}
        for field in sorted(names):
            pointer = spec["fields"].get(field)
            if pointer is None:
                record[field] = None
                record["unknown_fields"][field] = "adapter field mapping is required"
                continue
            record["field_sources"][field] = reader.source(spec["path"], base + pointer)
            try:
                value = lookup(raw, pointer)
                if field == "supersedes":
                    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value) or len(set(value)) != len(value):
                        raise ViewError("supersedes must be an explicit array of unique IDs")
                elif not isinstance(value, str) or not value.strip():
                    raise ViewError("mapped field must be nonempty text")
                if field in {"status", "relation"}:
                    record["recorded_" + field] = value
                    value = spec.get(field + "_map", {}).get(value, value)
                    if value not in STATES[name]:
                        raise ViewError("unmapped state; no inference from prose")
                record[field] = value
            except (ValueError, TypeError) as exc:
                record[field] = None
                record["unknown_fields"][field] = str(exc)
        if record.get("path"):
            try:
                reader.read(record["path"])
            except ViewError:
                pass
            record["content_source"] = reader.source(record["path"])
        result.append(record)
    duplicate_ids = sorted(key for key, count in Counter(r["id"] for r in result if r["id"]).items() if count > 1)
    return {"status": "known", "source": selected["source"], "records": result, "duplicate_ids": duplicate_ids}


def choose_active(issues, version):
    active = [r for r in issues["records"] if r.get("status") == "active"]
    result = {"status": "none", "count": len(active), "id": None,
              "candidates": [{"id": r["id"], "source": r["source"]} for r in active],
              "next_action": unknown("no active issue; recover the next action from actual user scope")}
    if issues["status"] != "known" or issues.get("duplicate_ids") or any(r["id"] is None or r["status"] is None for r in issues["records"]):
        result.update(status="unknown", reason="issue collection, IDs or statuses are incomplete or conflicting")
    elif len(active) > 1:
        result.update(status="conflict", reason="multiple active issues; no newest-record tie-break")
    elif len(active) == 1:
        item = active[0]
        if version["status"] != "known" or item["version"] != version["value"]:
            result.update(status="unknown", reason="active issue version is unknown or differs from active version")
        else:
            result.update(status="unique", id=item["id"])
            result["next_action"] = unknown(item["unknown_fields"].get("next_action", "next action is unresolved"), item["source"])
            if item["next_action"] is not None:
                result["next_action"] = {"status": "known", "value": item["next_action"],
                                         "source": item["field_sources"]["next_action"]}
    return result


def decision_state(collection, version):
    rows = collection["records"]
    by_id = {r["id"]: r for r in rows if r["id"]}
    errors = []
    if collection["status"] != "known" or collection.get("duplicate_ids"):
        errors.append("decision collection is unavailable or IDs are duplicated")
    edges = []
    # Only adopted decisions retire predecessors. Rejected/deferred proposals
    # retain their disposition and never acquire authority through an edge.
    for row in rows:
        if any(row.get(k) is None for k in ("id", "status", "topic", "version", "supersedes")):
            errors.append(f"decision fields unresolved at {row['source']['pointer']}")
        if row.get("status") in {"adopted", "superseded"}:
            for old in row.get("supersedes") or []:
                edges.append({"from": row["id"], "to": old, "source": row["field_sources"]["supersedes"]})
                if old not in by_id or old == row["id"]:
                    errors.append(f"unresolved or self supersession: {row['id']} -> {old}")
    graph = defaultdict(list)
    for edge in edges:
        graph[edge["from"]].append(edge["to"])
    visiting, done = set(), set()
    def visit(node):
        if node in visiting:
            errors.append("supersession cycle")
            return
        if node in done:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child)
        visiting.remove(node)
        done.add(node)
    for key in list(graph):
        visit(key)
    retired = {e["to"] for e in edges} | {r["id"] for r in rows if r["status"] == "superseded"}
    candidates = [r for r in rows if r["status"] == "adopted" and r["id"] not in retired
                  and version["status"] == "known" and r["version"] == version["value"]]
    topics = defaultdict(list)
    for row in candidates:
        topics[row["topic"]].append(row["id"])
    conflicts = [{"topic": topic, "ids": ids} for topic, ids in topics.items() if len(ids) > 1]
    if conflicts:
        errors.append("multiple adopted decisions in the same topic/version without supersession")
    if version["status"] != "known":
        errors.append("active version is unknown")
    return {"status": "unknown" if errors else "resolved", "effective_ids": [] if errors else [r["id"] for r in candidates],
            "superseded_ids": sorted(x for x in retired if x), "supersession": edges,
            "conflicts": conflicts, "reasons": sorted(set(errors))}


def quote_section(reader, spec):
    try:
        lines = reader.read(spec["path"]).decode("utf-8").splitlines()
        found = [i for i, line in enumerate(lines) if line == spec["heading"]]
        if len(found) != 1:
            raise ViewError("exact heading must occur once; adapter locator needs adjustment")
        start = found[0]
        level = len(spec["heading"].split(" ", 1)[0])
        end = next((i for i in range(start + 1, len(lines))
                    if re.match(r"^#{1," + str(level) + r"} ", lines[i])), len(lines))
        return {"status": "quoted-only", "text": "\n".join(lines[start:end]),
                "source": {**reader.source(spec["path"]), "heading": spec["heading"], "line_start": start + 1, "line_end": end}}
    except (ValueError, UnicodeError) as exc:
        return {"status": "unknown", "reason": str(exc), "source": {**reader.source(spec["path"]), "heading": spec["heading"]}}


def report_view(reader, spec):
    result = {"recorded_result": scalar(reader, spec), "freshness": "unknown", "inputs": [],
              "validity": "unknown; a cached result is not a live check, and dependency completeness is not established"}
    if "dependencies" not in spec:
        return result
    dep = spec["dependencies"]
    selected = reader.select(dep)
    result["dependency_source"] = selected["source"]
    if selected["status"] != "known" or not isinstance(selected["value"], list) or not selected["value"]:
        return result
    states = []
    for index, row in enumerate(selected["value"]):
        item = {"source": reader.source(dep["path"], dep["pointer"] + "/" + str(index)), "status": "unknown"}
        try:
            path, expected = (lookup(row, dep["fields"][key]) for key in ("path", "sha256"))
            if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
                raise ViewError("input hash missing or invalid")
            safe_path(reader.root, path)
            item.update(path=path, expected_sha256=expected)
            try:
                reader.read(path)
            except ViewError:
                pass
            item["actual_source"] = reader.source(path)
            item["status"] = "unchanged" if item["actual_source"]["sha256"] == expected else "changed-or-missing"
        except (ValueError, TypeError) as exc:
            item["reason"] = str(exc)
        states.append(item["status"])
        result["inputs"].append(item)
    if "changed-or-missing" in states:
        result["freshness"] = "stale"
    elif states and all(state == "unchanged" for state in states):
        result["freshness"] = "registered-inputs-unchanged"
    return result


def evidence_changes(current, previous):
    result = {"comparison": "no-baseline", "added_ids": [], "withdrawn_ids": [], "removed_ids": [], "changed_ids": []}
    if previous is None:
        return result
    old = previous.get("evidence", {})
    if current["status"] != "known" or old.get("status") != "known" or current.get("duplicate_ids") or old.get("duplicate_ids"):
        result["comparison"] = "unknown"
        return result
    for collection in (current, old):
        rows = collection.get("records")
        if (not isinstance(rows, list) or any(not isinstance(row, dict)
                or not isinstance(row.get("id"), str) or not row["id"]
                or row.get("status") not in STATES["evidence"] for row in rows)
                or len({row["id"] for row in rows}) != len(rows)):
            result["comparison"] = "unknown"
            return result
    before = {r["id"]: r for r in old.get("records", []) if r.get("id")}
    after = {r["id"]: r for r in current["records"] if r.get("id")}
    result.update(comparison="mapped-record-difference-only", added_ids=sorted(after.keys() - before.keys()),
                  removed_ids=sorted(before.keys() - after.keys()))
    result["withdrawn_ids"] = sorted(key for key, row in after.items() if row["status"] == "withdrawn"
                                     and (key not in before or before[key].get("status") != "withdrawn"))
    fields = FIELDS["evidence"]
    result["changed_ids"] = sorted(key for key in before.keys() & after.keys()
                                   if any(before[key].get(field) != after[key].get(field) for field in fields))
    return result


def check_view(root, view):
    if not isinstance(view, dict) or view.get("schema") != SCHEMA or not isinstance(view.get("sources"), list) or not view["sources"]:
        raise ViewError("not a saved resume view with source fingerprints")
    reader = Reader(root)
    changes = []
    for expected in view["sources"]:
        try:
            reader.read(expected["path"])
        except ViewError:
            pass
        actual = reader.source(expected["path"])
        if actual != expected:
            changes.append({"path": expected["path"], "before": expected, "now": actual})
    return {"schema": "research-resume-freshness.v1", "freshness": "stale" if changes else "current",
            "changes": changes, "scope": "Source byte identity only; no authority or scientific certification."}


def build_view(root, adapter_path, previous_path=None):
    reader = Reader(root)
    adapter = parse(reader.read(adapter_path))
    validate_adapter(adapter)
    previous = parse(reader.read(previous_path)) if previous_path else None
    if previous is not None and (not isinstance(previous, dict) or previous.get("schema") != SCHEMA):
        raise ViewError("--previous must be a saved resume view; used for differences only")
    objective = scalar(reader, adapter.get("objective"))
    version = scalar(reader, adapter.get("active_version"))
    collections = {name: records(reader, adapter.get(name), name) for name in FIELDS}
    active = choose_active(collections["issues"], version)
    artifacts = {"affected_ids": [], "unrelated_ids": [], "unresolved_ids": []}
    for row in collections["artifacts"]["records"]:
        # A historical file can be explicitly affected by a newer research
        # target. Keep file version separate from the declared relation scope.
        relation_version = row.get("relation_version", row["version"])
        usable = (active["status"] == "unique" and row["issue_id"] == active["id"]
                  and version["status"] == "known" and relation_version == version["value"]
                  and not collections["artifacts"].get("duplicate_ids"))
        bucket = row["relation"] + "_ids" if usable and row["relation"] in {"affected", "unrelated"} else "unresolved_ids"
        artifacts[bucket].append(row["id"])
    quotes = [quote_section(reader, spec) for spec in adapter.get("quotes", [])]
    reports = [report_view(reader, spec) for spec in adapter.get("reports", [])]
    result = {"schema": SCHEMA, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "scope": LIMIT, "authority": False, "objective": objective, "active_version": version,
              **collections, "active_issue": active,
              "decision_resolution": decision_state(collections["decisions"], version),
              "evidence_changes": evidence_changes(collections["evidence"], previous),
              "artifact_scope": artifacts, "quotes": quotes, "reports": reports,
              "sources": sorted(reader.sources.values(), key=lambda row: row["path"])}
    if previous is not None:
        result["previous_view"] = {"path": previous_path, "sha256": reader.source(previous_path)["sha256"],
                                   "freshness": check_view(root, previous)["freshness"], "role": "comparison only; never authority"}
    # Detect source edits during this build instead of publishing a mixed snapshot.
    result["freshness"] = check_view(root, result)["freshness"]
    return result


def markdown(view):
    def cell(item):
        return str(item["value"]) if item["status"] == "known" else "unknown"
    active = view["active_issue"]
    decisions = view["decision_resolution"]
    changes = view["evidence_changes"]
    def locator(source):
        return source["path"] + "#" + source.get("pointer", "")
    def describe(row):
        origin = f"{row.get('source_kind') or 'unknown'} / {row.get('source_locator') or 'unknown'}"
        return f"{row['id']}: {row.get('summary') or 'unknown'} [{locator(row['source'])}; origin={origin}]"
    lines = [f"目标：{cell(view['objective'])}；active version：{cell(view['active_version'])}",
             f"活动项：{active['id'] or active['status']}（active 数量：{active['count']}）；视图：{view['freshness']}",
             f"当前有效决定：{', '.join(decisions['effective_ids']) or decisions['status']}；已替代：{', '.join(decisions['superseded_ids']) or 'none'}",
             f"证据变化（{changes['comparison']}）：新增 {changes['added_ids']}；撤回 {changes['withdrawn_ids']}；移出记录 {changes['removed_ids']}；修改 {changes['changed_ids']}",
             f"产物范围：{json.dumps(view['artifact_scope'], ensure_ascii=False)}",
             f"下一步：{cell(active['next_action'])}"]
    if active["status"] == "unique":
        lines.append("活动项原记录：" + describe(next(row for row in view["issues"]["records"] if row["id"] == active["id"])))
    lines.extend("决定原记录：" + describe(row) for row in view["decisions"]["records"] if row["id"] in decisions["effective_ids"])
    changed_evidence = set(changes["added_ids"] + changes["withdrawn_ids"] + changes["changed_ids"])
    lines.extend("证据原记录：" + describe(row) for row in view["evidence"]["records"] if row["id"] in changed_evidence)
    for row in view["artifacts"]["records"]:
        lines.append(f"产物原记录：{row['id']} / {row.get('path') or 'unknown'}；"
                     f"file version={row.get('version') or 'unknown'}；"
                     f"relation version={row.get('relation_version', row.get('version')) or 'unknown'}；"
                     f"[{locator(row['source'])}]")
    if active.get("reason"):
        lines.append("活动项待核实：" + active["reason"])
    if decisions["reasons"]:
        lines.append("决定待核实：" + "; ".join(decisions["reasons"]))
    for report in view["reports"]:
        lines.append(f"登记报告：{cell(report['recorded_result'])}；freshness={report['freshness']}；validity=unknown")
    for quote in view["quotes"]:
        source = quote["source"]
        excerpt = quote.get("text", "unknown: " + quote.get("reason", ""))
        lines.append(f"仅引文 {source['path']} / {source['heading']}：\n" + "\n".join("> " + line for line in excerpt.splitlines()))
    lines.extend(["", LIMIT, "", "来源（JSON 输出保留逐字段 pointer）："])
    lines.extend(f"- {source['path']} — {source['sha256'] or source['status']}" for source in view["sources"])
    return "\n\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--project", required=True)
    build.add_argument("--adapter", required=True)
    build.add_argument("--previous")
    build.add_argument("--format", choices=("json", "markdown"), default="json")
    check = sub.add_parser("check")
    check.add_argument("--project", required=True)
    check.add_argument("--view", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.project)
        if not root.is_absolute() or not root.is_dir():
            raise ViewError("--project must be an existing absolute directory")
        root = root.resolve()
        if args.command == "build":
            result = build_view(root, args.adapter, args.previous)
            print(markdown(result) if args.format == "markdown" else json.dumps(result, ensure_ascii=False, indent=2))
            unresolved = (result["freshness"] != "current" or result["active_issue"]["status"] in {"unknown", "conflict"}
                          or result["decision_resolution"]["status"] == "unknown"
                          or any(result[key]["status"] == "unknown" for key in ("objective", "active_version")))
            return 1 if unresolved else 0
        result = check_view(root, parse(read_bytes(root, args.view)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["freshness"] == "current" else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc), "status": "invalid-adapter-or-view"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
