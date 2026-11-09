#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "bin/mwhc"
GRAPH = ROOT / "tests/tiny.hgr"

for algorithm in ("allrootpath", "medoidpath", "fastpath"):
    output = subprocess.check_output([
        BINARY, "--input", GRAPH, "--query", "0,3,5", "--algo", algorithm
    ], text=True)
    result = json.loads(output)
    assert result["feasible"]
    assert {0, 3, 5}.issubset(result["selected"])
    assert result["cost"] > 0
print("three-algorithm smoke test passed")
