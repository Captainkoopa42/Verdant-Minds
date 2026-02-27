#!/usr/bin/env python3

import random
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.memory.memory_web import MemoryWeb


def _strip_connection(web: MemoryWeb, a: str, b: str):
    if web.graph.has_edge(a, b):
        web.graph.remove_edge(a, b)
    web.memory_store[a]["connections"] = [c for c in web.memory_store[a]["connections"] if c[0] != b]
    web.memory_store[b]["connections"] = [c for c in web.memory_store[b]["connections"] if c[0] != a]


def test_pconnect_edge_policy_rejects_some_large_delta_edges():
    random.seed(7)

    web = MemoryWeb()
    accepted = 0
    rejected = 0

    for i in range(40):
        a = f"non maleficence concept {i}"
        b = f"transparency concept {i}"
        web.add_thought(a, stability=1.0)
        web.add_thought(b, stability=1.0)
        _strip_connection(web, a, b)

        ok = web.connect_thoughts(a, b, initial_weight=0.05, edge_policy="pconnect")
        if ok:
            accepted += 1
            assert web.graph.has_edge(a, b)
            assert "delta_e" in web.graph[a][b]
        else:
            rejected += 1

    assert rejected > 0
    assert accepted > 0
