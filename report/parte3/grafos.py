"""Caracteriza os grafos p3_W_1..5 e grava grafos.json. Uso: python3 grafos.py (precisa de numpy e pandas)."""
import json, os
import numpy as np, pandas as pd

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DESTINO = 100


def csr(a, b, V):
    o = np.argsort(a, kind="stable")
    ptr = np.zeros(V + 2, np.int64)
    np.cumsum(np.bincount(a, minlength=V + 1), out=ptr[1:])
    return ptr, b[o]


def bfs(ptr, idx, V, s):
    d = np.full(V + 1, -1, np.int32); d[0] = -2; d[s] = 0
    fr = np.array([s]); L = 0; tam = []
    while fr.size:
        st, ln = ptr[fr], ptr[fr + 1] - ptr[fr]; tot = int(ln.sum())
        if tot == 0:
            break
        pos = np.repeat(st - np.cumsum(ln) + ln, ln) + np.arange(tot)
        nb = idx[pos]; nb = np.unique(nb[d[nb] == -1])
        if nb.size == 0:
            break
        L += 1; d[nb] = L; fr = nb; tam.append(int(nb.size))
    return d, tam


def analisa(n):
    arq = os.path.join(RAIZ, "data", f"p3_W_{n}.txt")
    with open(arq) as f:
        V = int(f.readline())
    df = pd.read_csv(arq, sep=r"\s+", skiprows=1, header=None, names=["u", "v", "w"],
                     dtype={"u": np.int32, "v": np.int32, "w": np.float64}, engine="c")
    u, v, w = df.u.values, df.v.values, df.w.values
    E = len(u)
    outd = np.bincount(u, minlength=V + 1)[1:]
    ks = np.sort(u.astype(np.int64) * (V + 1) + v)
    rev = v.astype(np.int64) * (V + 1) + u
    gap = np.abs(u.astype(np.int64) - v) / V
    bu = (u - 1).astype(np.int64) * 11 // V
    bv = (v - 1).astype(np.int64) * 11 // V
    # BFS do 100 pelas arestas reversas (quem chega ao 100) e pelas diretas (quem o 100 alcança)
    d_rev, tam = bfs(*csr(v, u, V), V, DESTINO)
    d_fw, _ = bfs(*csr(u, v, V), V, DESTINO)
    return {
        "nome": f"W_{n}", "V": V, "E": E,
        "grau_saida": {"media": round(float(outd.mean()), 1), "min": int(outd.min()), "max": int(outd.max())},
        "pesos": {"min": float(w.min()), "max": float(w.max()), "negativos": int((w < 0).sum())},
        "reciprocidade": round(float(np.isin(rev, ks).mean()), 4),
        "gap_medio_sobre_V": round(float(gap.mean()), 4),
        "corte_11_faixas": round(float((bu != bv).mean()), 4),
        "fortemente_conexo": bool((d_fw >= 0).sum() == V and (d_rev >= 0).sum() == V),
        "saltos_ate_100": len(tam),
    }


if __name__ == "__main__":
    out = {"grafos": []}
    for n in range(1, 6):
        r = analisa(n); out["grafos"].append(r); print(r, flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "grafos.json"), "w"), indent=1)
