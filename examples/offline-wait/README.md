# Offline wait example

This synthetic example demonstrates the operational rule for a long local
simulation or other offline job:

1. record the operation and its real handle;
2. enter `waiting` with result-dependent actions suspended;
3. refuse a downstream result-writing operation while the dependency is not
   terminal;
4. record the terminal event and result artifact;
5. clear the wait barrier only after the terminal record is valid.

Run from the repository root:

```bash
python3 scripts/smoke_offline_wait.py
```

The script uses a temporary synthetic project and no network. It exercises the
state contract; it does not launch a real production simulation or establish a
scientific result.
