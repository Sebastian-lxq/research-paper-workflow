#!/usr/bin/env python3
"""Render the public synthetic workflow demo as an animated GIF and poster."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - optional maintainer tool
    raise SystemExit("Install Pillow to render the demo: python3 -m pip install Pillow") from exc


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "assets"
GIF_PATH = OUTPUT_DIR / "workflow-demo.gif"
POSTER_PATH = OUTPUT_DIR / "workflow-demo-poster.png"
WIDTH, HEIGHT = 1280, 720

BACKGROUND = "#070B17"
PANEL = "#0D1428"
PANEL_ALT = "#111C35"
TEXT = "#E8EEF9"
MUTED = "#93A4BD"
BLUE = "#60A5FA"
CYAN = "#2DD4BF"
VIOLET = "#818CF8"
AMBER = "#FBBF24"
GREEN = "#4ADE80"
RED = "#FB7185"


@dataclass(frozen=True)
class Slide:
    step: str
    title: str
    eyebrow: str
    left_title: str
    left_lines: tuple[tuple[str, str], ...]
    right_title: str
    right_lines: tuple[tuple[str, str], ...]
    footer: str
    duration_ms: int


SLIDES = (
    Slide(
        "00–05 s",
        "From a broad direction to the next safe research action",
        "SYNTHETIC METHODS-PAPER DEMO",
        "Input",
        (("Specification testing", TEXT), ("+ flexible nuisance learner", BLUE)),
        "Promise",
        (("Inspect evidence before claims", CYAN), ("Persist resumable state", VIOLET)),
        "No private data · no invented theorem · no fabricated simulation result",
        5000,
    ),
    Slide(
        "05–12 s",
        "Read the project brief and preserve what is still unknown",
        "1 · INSPECT",
        "Research brief",
        (
            ("Classical calibration may fail", TEXT),
            ("when nuisance estimation is slow.", TEXT),
            ("No literature search yet.", AMBER),
        ),
        "Frozen constraints",
        (
            ("No external data", MUTED),
            ("No proof or code", MUTED),
            ("Do not claim novelty", RED),
        ),
        "The workflow starts from artifacts that exist—not from a completed-paper fiction.",
        7000,
    ),
    Slide(
        "12–19 s",
        "One prompt starts or resumes the workflow",
        "2 · START",
        "Prompt",
        (
            ("Use $research-paper-workflow", BLUE),
            ("to inspect project-brief.md,", TEXT),
            ("compare candidate mechanisms,", TEXT),
            ("and identify the cheapest", TEXT),
            ("safe next action.", CYAN),
        ),
        "Guardrail",
        (
            ("Do not claim novelty", RED),
            ("or create numerical results.", RED),
        ),
        "The same command can resume an existing .paper/workflow state.",
        7000,
    ),
    Slide(
        "19–26 s",
        "Classify provisionally and expose missing evidence",
        "3 · ORIENT",
        "Current state",
        (
            ("paper_type: methods", BLUE),
            ("simulation: deferred", AMBER),
            ("literature: pending", AMBER),
        ),
        "First unresolved requirement",
        (
            ("Map nearest-neighbor tests", TEXT),
            ("before contribution language", RED),
        ),
        "A provisional classification guides work without pretending uncertainty is resolved.",
        7000,
    ),
    Slide(
        "26–34 s",
        "Compare mechanisms, not cosmetic title variants",
        "4 · EXPLORE",
        "Candidate A",
        (
            ("Orthogonalized statistic", BLUE),
            ("Falsifier: linear toy model", MUTED),
        ),
        "Candidate B",
        (
            ("Calibration correction", VIOLET),
            ("Falsifier: fixed learner bias", MUTED),
        ),
        "Candidates remain provisional until literature and feasibility evidence arrive.",
        8000,
    ),
    Slide(
        "34–42 s",
        "Evidence gates stop unsupported downstream claims",
        "5 · GATE",
        "Blocked for now",
        (
            ("Novelty claim", RED),
            ("Theorem conclusion", RED),
            ("Simulation result", RED),
        ),
        "Safe to continue",
        (
            ("Search-plan design", GREEN),
            ("Toy-model specification", GREEN),
            ("State initialization", GREEN),
        ),
        "A blocked branch does not freeze independent work.",
        8000,
    ),
    Slide(
        "42–50 s",
        "Write a compact, resumable state",
        "6 · PERSIST",
        ".paper/workflow/status.json",
        (
            ("schema: paper-workflow-status.v1", MUTED),
            ("next_stage: framing", BLUE),
            ("scientific_result_claimed: false", GREEN),
        ),
        "Offline work",
        (
            ("Store the real job handle", TEXT),
            ("Resume after terminal state", CYAN),
            ("Never poll by conversation turn", MUTED),
        ),
        "The state records coordination facts, not a second scientific truth database.",
        8000,
    ),
    Slide(
        "50–60 s",
        "Deliver a bounded next action—not an invented paper",
        "7 · DELIVER",
        "Next action",
        (
            ("Search named and de-anchored", TEXT),
            ("nearest-neighbor paths, then", TEXT),
            ("run the cheapest toy falsifier.", CYAN),
        ),
        "Inspectable output",
        (
            ("Evidence gaps", BLUE),
            ("Candidate routes", VIOLET),
            ("Blockers + resume condition", AMBER),
        ),
        "Install from GitHub · run locally · keep every claim inside its evidence ceiling",
        10000,
    ),
)


def font_candidates(mono: bool) -> Iterable[Path]:
    names = (
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ) if mono else (
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/SFNSRounded.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    return (Path(name) for name in names)


def load_font(size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in font_candidates(mono):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


TITLE = load_font(42)
EYEBROW = load_font(18)
SECTION = load_font(20)
BODY = load_font(25, mono=True)
SMALL = load_font(17)


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str) -> None:
    draw.rounded_rectangle(box, radius=22, fill=fill, outline="#263450", width=2)


def draw_logo(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 77, 65
    draw.ellipse((45, 33, 109, 97), fill="#0A1730", outline=BLUE, width=3)
    draw.arc((57, 47, 97, 91), 195, 345, fill=CYAN, width=4)
    draw.arc((57, 43, 97, 87), 15, 165, fill=VIOLET, width=4)
    draw.ellipse((73, 61, 81, 69), fill=TEXT)


def draw_progress(draw: ImageDraw.ImageDraw, index: int) -> None:
    x0, y, total = 930, 69, 275
    draw.rounded_rectangle((x0, y, x0 + total, y + 8), radius=4, fill="#22304B")
    completed = int(total * (index + 1) / len(SLIDES))
    draw.rounded_rectangle((x0, y, x0 + completed, y + 8), radius=4, fill=CYAN)


def draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: tuple[tuple[str, str], ...],
    x: int,
    y: int,
) -> None:
    for text, color in lines:
        draw.text((x, y), text, font=BODY, fill=color)
        y += 42


def render_slide(slide: Slide, index: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw_logo(draw)
    draw.text((128, 48), "RESEARCH PAPER WORKFLOW", font=EYEBROW, fill=MUTED)
    draw.text((1095, 42), slide.step, font=SMALL, fill=MUTED)
    draw_progress(draw, index)

    draw.text((72, 130), slide.eyebrow, font=EYEBROW, fill=CYAN)
    draw.text((72, 166), slide.title, font=TITLE, fill=TEXT)

    left = (72, 255, 622, 575)
    right = (658, 255, 1208, 575)
    rounded_panel(draw, left, PANEL)
    rounded_panel(draw, right, PANEL_ALT)
    draw.text((104, 285), slide.left_title, font=SECTION, fill=BLUE)
    draw.text((690, 285), slide.right_title, font=SECTION, fill=VIOLET)
    draw_lines(draw, slide.left_lines, 104, 335)
    draw_lines(draw, slide.right_lines, 690, 335)

    draw.line((72, 628, 1208, 628), fill="#263450", width=2)
    draw.text((72, 653), slide.footer, font=SMALL, fill=MUTED)
    draw.text((1161, 652), f"{index + 1}/{len(SLIDES)}", font=SMALL, fill=CYAN)
    return image


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = [render_slide(slide, index) for index, slide in enumerate(SLIDES)]
    durations = [slide.duration_ms for slide in SLIDES]
    frames[0].save(
        GIF_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    frames[-1].save(POSTER_PATH, optimize=True)
    if sum(durations) != 60000:
        raise SystemExit("demo duration must total exactly 60 seconds")
    print(GIF_PATH)
    print(POSTER_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
