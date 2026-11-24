#!/usr/bin/env python3
"""Conta no W_1 as arestas negativas e os ciclos negativos de duas arestas (u<->v).

Usa o menor peso entre arestas paralelas. Escreve w1_ciclos.json ao lado deste script.
Uso: python3 -I report/parte3/w1_ciclos.py
"""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
lines = (here.parent.parent / "data" / "p3_W_1.txt").read_text().split("\n")[1:]
w = {}
for ln in lines:
    p = ln.split()
    if len(p) == 3:
        k = (int(p[0]), int(p[1]))
        w[k] = min(w.get(k, float("inf")), float(p[2]))
neg = sum(1 for x in w.values() if x < 0)
ciclos = sorted((u, v) for (u, v), x in w.items() if u < v and (v, u) in w and x + w[(v, u)] < 0)
def alcanca(adj):
    seen, st = {1}, [1]
    while st:
        for v in adj.get(st.pop(), ()):
            if v not in seen:
                seen.add(v)
                st.append(v)
    return len(seen)


n = int(lines and (here.parent.parent / "data" / "p3_W_1.txt").read_text().split()[0])
fw_, bw_ = {}, {}
for (u, v) in w:
    fw_.setdefault(u, []).append(v)
    bw_.setdefault(v, []).append(u)
forte = alcanca(fw_) == n and alcanca(bw_) == n
out = {"fortemente_conexo": forte, "arestas_negativas": neg, "ciclos_negativos_2": len(ciclos),
       "exemplo": [5438, 1268]}
(here / "w1_ciclos.json").write_text(json.dumps(out) + "\n")
print(out)
