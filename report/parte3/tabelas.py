#!/usr/bin/env python3
"""Gera report/parte3/tabelas.tex (e relax.txt) a partir de report/parte3/data.json.

Uso: python3 -I report/parte3/tabelas.py   (data.json vem de bench/summarize_p3.py)
O relatório só usa \\dado{chave} e as tabelas geradas aqui; nenhum número é digitado à mão.
Valores ausentes (benchmark em andamento) viram "---".
"""
import json
import math
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent.parent
data = json.loads((here / "data.json").read_text())
machine, graphs = data["machine"], data["graphs"]
by = {g["name"]: g for g in graphs}

# Conferência independente do W_2 (Dijkstra em Python, feito à parte; vem do enunciado da tarefa).
REF_W2_BF = {"10": 10.47, "20": 8.48, "30": 8.71}
REF_W2_MATRIX = [[0, 11.73, 8.14, 9.49, 7.08], [3.84, 0, 7.03, 8.3, 4.7],
                 [5.79, 12.55, 0, 8.3, 6.33], [5.05, 12.32, 5.36, 0, 5.71],
                 [4.48, 12.23, 7.79, 8.26, 0]]
# Contagem de verificações de tests/graph_tests.cpp (execução registrada, não recalculada aqui).
TEST_CHECKS = 55823939

DASH = "---"


# ── formatação em pt-BR ─────────────────────────────────────────────────────
def num(x, d=0):
    if x is None:
        return DASH
    s = f"{abs(x):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("$-$" if x < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else "") + s


def dur(s):
    if s is None:
        return DASH
    if s < 1e-3:
        return num(s * 1e6, 0 if s >= 1e-4 else 1) + "\\,\\textmu s"
    if s < 1:
        return num(s * 1000, 2 if s < 0.01 else 1) + "\\,ms"
    if s < 120:
        return num(s, 2) + "\\,s"
    if s < 7200:
        return num(s / 60, 1) + "\\,min"
    if s < 172800:
        return num(s / 3600, 1) + "\\,h"
    if s < 2 * 365 * 86400:
        return num(s / 86400, 1 if s < 100 * 86400 else 0) + "\\,dias"
    y = s / (365 * 86400)
    return num(y, 1 if y < 100 else 0) + "\\,anos"


def dur_pm(mean, std):
    """Média ± desvio na unidade da média, com as mesmas casas."""
    if mean is None or std is None:
        return dur(mean)
    text = dur(mean)
    value, _, unit = text.partition("\\,")
    scale = {"\\textmu s": 1e-6, "ms": 1e-3, "s": 1.0, "min": 60.0, "h": 3600.0,
             "dias": 86400.0, "anos": 365 * 86400.0}[unit]
    places = len(value.split(",")[1]) if "," in value else 0
    return f"{value} $\\pm$ {num(std / scale, places)}\\,{unit}"


def size(b):
    if b is None:
        return DASH
    for scale, unit in ((1e15, "PB"), (1e12, "TB"), (1e9, "GB")):
        if b >= 999.5 * scale / 1000:
            return num(b / scale, 1 if b / scale < 10 else 0) + "\\," + unit
    return num(b / 1e6, 0) + "\\,MB"


def sci(x):
    if x is None:
        return DASH
    e = int(math.floor(math.log10(x)))
    return f"${num(x / 10 ** e, 2).replace(',', '{,}')}\\cdot10^{{{e}}}$"


def times(x):
    if x is None:
        return DASH
    return (num(x, 1) if x < 100 else num(x)) + "$\\times$"


def tex(name):
    base, _, k = name.partition("_")
    return f"\\W{{{k}}}"


dados = {}


def dado(key, value):
    dados[key] = value


out = []

# ── máquina ─────────────────────────────────────────────────────────────────
ram = machine["memory_bytes"]
nthreads = machine["threads"]
dado("cpu", machine["cpu"] or DASH)
dado("ram", num(ram / 2**30) + "\\,GiB" if ram else DASH)
dado("threads", str(nthreads))
dado("compiler", (machine["compiler"] or DASH).split(" (")[0])
limit = next((g["floyd_warshall"]["limit_gib"] for g in graphs
              if g["floyd_warshall"]["limit_gib"]), None)
dado("limit", num(limit) + "\\,GiB" if limit else DASH)
dado("tests", num(TEST_CHECKS))


def measured(g, part):
    """Tempo médio e desvio de `part`, ou None."""
    p = g[part]
    return (p["mean_s"], p["std_s"]) if p["status"] in ("ok", "ciclo_negativo") else (None, None)


# ── por grafo ───────────────────────────────────────────────────────────────
fw_ref = None  # W_2: Floyd-Warshall completo medido, base da estimativa por V^3
for g in graphs:
    if g["floyd_warshall"]["status"] == "ok" and g["floyd_warshall"]["mean_s"]:
        fw_ref = g

for g in graphs:
    n = g["name"]
    V, E = g["vertices"], g["edges"]
    bf, fw, ap, ops = g["bellman_ford"], g["floyd_warshall"], g["all_pairs_bf"], g["ops"]
    dado(f"{n}.V", num(V))
    dado(f"{n}.E", num(E))
    dado(f"{n}.deg", num(2 * E / V, 1) if V else DASH)
    dado(f"{n}.neg", DASH if g["negative_weights"] is None else
         ("sim" if g["negative_weights"] else "não"))
    dado(f"{n}.fwmem", size(fw["memory_needed_bytes"]))
    dado(f"{n}.fwmem.gib", num(fw["memory_needed_gib"], 1) + "\\,GiB" if V else DASH)
    dado(f"{n}.bf", dur(bf["mean_s"]))
    dado(f"{n}.bf.rounds", num(bf["rounds"]))
    dado(f"{n}.bf.runs", num(bf["runs"]))
    dado(f"{n}.fw", dur(fw["mean_s"]))
    dado(f"{n}.ap", dur(ap["mean_s"]))
    dado(f"{n}.ap.sample", num(ap["sample"]))
    dado(f"{n}.ops.fw", sci(ops["fw_relaxations"]))
    dado(f"{n}.ops.bf", sci(ops["bf_ops_upper_bound"]))
    if ops["fw_relaxations"] and ops["bf_ops_upper_bound"]:
        dado(f"{n}.ops.ratio", times(ops["fw_relaxations"] / ops["bf_ops_upper_bound"]))
    # Custo por aresta do Bellman-Ford até um destino (limite superior de arestas).
    if bf["mean_s"] and bf["rounds"] and bf["status"] == "ok":
        dado(f"{n}.bf.nsedge", num(bf["mean_s"] / (bf["rounds"] * E) * 1e9, 2))
    if fw["status"] == "ok" and fw["mean_s"]:
        dado(f"{n}.fw.ps", num(fw["mean_s"] / ops["fw_relaxations"] * 1e12, 0))
    if ap["status"] == "ok" and ap["mean_s"] and ops["bf_ops_upper_bound"]:
        # Tempo de parede dividido pelo limite de arestas examinadas, em ns.
        dado(f"{n}.ap.nsedge", num(ap["mean_s"] / ops["bf_ops_upper_bound"] * 1e9, 2))
        dado(f"{n}.ap.nsedge.cpu",
             num(ap["mean_s"] * (ap["threads"] or 1) / ops["bf_ops_upper_bound"] * 1e9, 2))
    dado(f"{n}.ap.threads", num(ap["threads"]))
    if fw["status"] == "ok" and fw["mean_s"] and ap["status"] == "ok" and ap["mean_s"]:
        dado(f"{n}.q4", "")  # marcador: há comparação medida
    # Estimativa do Floyd-Warshall por V^3 a partir da execução completa medida.
    est = None
    if fw["status"] == "memoria_insuficiente" and fw_ref and V:
        est = fw_ref["floyd_warshall"]["mean_s"] * (V / fw_ref["vertices"]) ** 3
    dado(f"{n}.fwest", dur(est))
    g["_fw_est"] = est

dado("fwref.name", tex(fw_ref["name"]) if fw_ref else DASH)
dado("fwref.fw", dur(fw_ref["floyd_warshall"]["mean_s"]) if fw_ref else DASH)
dado("fwref.fwpm", dur_pm(fw_ref["floyd_warshall"]["mean_s"],
                          fw_ref["floyd_warshall"]["std_s"]) if fw_ref else DASH)

# Menor/maior grau, para a tabela de grafos.
degs = [2 * g["edges"] / g["vertices"] for g in graphs if g["vertices"]]

# ── tabela de grafos ────────────────────────────────────────────────────────
rows = []
for g in graphs:
    n = g["name"]
    rows.append(" & ".join([
        tex(n), f"\\dado{{{n}.V}}", f"\\dado{{{n}.E}}", f"\\dado{{{n}.deg}}",
        f"\\dado{{{n}.neg}}", f"\\dado{{{n}.fwmem}}"]) + "\\\\")
out.append("\\newcommand{\\tabelaGrafos}{" + "\n".join(rows) + "}")

# ── tabela de distâncias até o vértice 100 ──────────────────────────────────
rows = []
for s in ("10", "20", "30"):
    cells = []
    for g in graphs:
        bf = g["bellman_ford"]
        if bf["status"] == "ciclo_negativo":
            cells.append("$-\\infty$")
        elif bf["status"] == "ok":
            d = bf["distances"][s]
            cells.append(num(d, 2) if d is not None else "$\\infty$")
        else:
            cells.append(DASH)
    rows.append(f"{s} & " + " & ".join(cells) + "\\\\")
out.append("\\newcommand{\\tabelaDistancias}{" + "\n".join(rows) + "}")
neg_graphs = [g["name"] for g in graphs if g["bellman_ford"]["status"] == "ciclo_negativo"]
dado("neg.list", ", ".join(tex(n) for n in neg_graphs) or DASH)

# ── matrizes 5x5 ────────────────────────────────────────────────────────────
V5 = (10, 20, 30, 40, 50)


def matrix_tabular(g):
    m = g["matrix"]
    head = " & ".join(f"\\textbf{{{v}}}" for v in V5)
    lines = ["\\begin{tabular}{@{}r|rrrrr@{}}", f" & {head}\\\\ \\midrule"]
    for i, s in enumerate(V5):
        if m["rows"]:
            cells = [("0" if x == 0 else num(x, 2)) if x is not None else "$\\infty$"
                     for x in m["rows"][i]]
        else:
            cells = [DASH] * 5
        lines.append(f"\\textbf{{{s}}} & " + " & ".join(cells) + "\\\\")
    lines.append("\\end{tabular}")
    return "\n".join(lines)


for g in graphs:
    out.append(f"\\expandafter\\def\\csname matriz@{g['name']}\\endcsname{{{matrix_tabular(g)}}}")
    src = {"floyd_warshall": "Floyd-Warshall", "bellman_ford": "Bellman-Ford, um por destino",
           None: ("ciclo negativo" if g["bellman_ford"]["status"] == "ciclo_negativo"
                  else "em execução")}[g["matrix"]["source"]]
    dado(f"{g['name']}.matsrc", src)
dado("matrix.bf.list", ", ".join(tex(g["name"]) for g in graphs
                                  if g["matrix"]["source"] == "bellman_ford") or DASH)

# ── tabela de tempos ────────────────────────────────────────────────────────
DAG = "\\textsuperscript{$\\dagger$}"
rows = []
for g in graphs:
    n = g["name"]
    bf, fw, ap = g["bellman_ford"], g["floyd_warshall"], g["all_pairs_bf"]
    c_bf = dur_pm(bf["mean_s"], bf["std_s"]) + (DAG if bf["status"] == "ciclo_negativo" else "")
    if fw["status"] == "memoria_insuficiente":
        c_fw = "\\textit{memória}"
    else:
        c_fw = dur_pm(fw["mean_s"], fw["std_s"]) + (DAG if fw["status"] == "ciclo_negativo" else "")
    c_ap = dur_pm(ap["mean_s"], ap["std_s"])
    if ap["estimated"] and ap["mean_s"] is not None:
        c_ap = f"\\textit{{{c_ap}}}"
    c_ap += DAG if ap["status"] == "ciclo_negativo" else ""
    rows.append(" & ".join([tex(n), f"\\dado{{{n}.bf.rounds}}", c_bf, c_fw, c_ap]) + "\\\\")
out.append("\\newcommand{\\tabelaTempos}{" + "\n".join(rows) + "}")

# ── tabela Floyd-Warshall x todos os pares por Bellman-Ford ──────────────────
rows = []
q4 = {}
for g in graphs:
    n = g["name"]
    bf, fw, ap, ops = g["bellman_ford"], g["floyd_warshall"], g["all_pairs_bf"], g["ops"]
    if bf["status"] == "ciclo_negativo":
        rows.append(f"{tex(n)} & \\dado{{{n}.ops.fw}} & \\dado{{{n}.ops.bf}} & "
                    f"{dur(fw['mean_s'])}{DAG} & {dur(ap['mean_s'])}{DAG} & {DASH}\\\\")
        continue
    fw_t, fw_est = fw["mean_s"], False
    if fw["status"] == "memoria_insuficiente":
        fw_t, fw_est = g["_fw_est"], True
    ap_t = ap["mean_s"]
    # Mesma base de threads: o Bellman-Ford estimado roda em 1 thread, o Floyd-Warshall em 11.
    ratio = None
    if fw_t and ap_t and fw["status"] != "pendente":
        fw_threads = fw["threads"] or (fw_ref["floyd_warshall"]["threads"] if fw_ref else 1)
        ratio = fw_t / (ap_t * (ap["threads"] or 1) / fw_threads)
    q4[n] = ratio
    cf = dur(fw_t)
    cf = f"\\textit{{{cf}}}" if fw_est and fw_t else cf
    ca = dur(ap_t)
    ca = f"\\textit{{{ca}}}" if ap["estimated"] and ap_t else ca
    rows.append(" & ".join([tex(n), f"\\dado{{{n}.ops.fw}}", f"\\dado{{{n}.ops.bf}}", cf, ca,
                            times(ratio) if ratio else DASH]) + "\\\\")
    if ratio:
        dado(f"{n}.q4.ratio", times(ratio if ratio >= 1 else 1 / ratio))
        dado(f"{n}.q4.winner", "Bellman-Ford" if ratio > 1 else "Floyd-Warshall")
        dado(f"{n}.q4.loser", "Floyd-Warshall" if ratio > 1 else "Bellman-Ford")
out.append("\\newcommand{\\tabelaQuatro}{" + "\n".join(rows) + "}")

# Custo por operação do W_2 (ou do primeiro grafo com as duas medições): razão de tempo e de operações.
for g in graphs:
    n = g["name"]
    fw, ap, ops = g["floyd_warshall"], g["all_pairs_bf"], g["ops"]
    if fw["status"] == "ok" and ap["status"] == "ok" and fw["mean_s"] and ap["mean_s"]:
        dado("cmp.name", tex(n))
        dado("cmp.ops", times(ops["fw_relaxations"] / ops["bf_ops_upper_bound"]))
        dado("cmp.time", times(max(fw["mean_s"] / ap["mean_s"], ap["mean_s"] / fw["mean_s"])))
        # Floyd-Warshall: ps por relaxação (parede); Bellman-Ford: ns por aresta do limite.
        dado("cmp.fw.ps", num(fw["mean_s"] / ops["fw_relaxations"] * 1e12, 0))
        dado("cmp.bf.ns", num(ap["mean_s"] / ops["bf_ops_upper_bound"] * 1e9, 2))
        c = (ap["mean_s"] / ops["bf_ops_upper_bound"]) / (fw["mean_s"] / ops["fw_relaxations"])
        dado("cmp.cost", times(c if c >= 1 else 1 / c) + (" mais" if c >= 1 else " menos"))

# ── conferência com a referência independente do W_2 ────────────────────────
w2 = by["W_2"]
problems = []
if w2["bellman_ford"]["status"] == "ok":
    for s, ref in REF_W2_BF.items():
        d = w2["bellman_ford"]["distances"][s]
        if d is None or abs(d - ref) > 0.0051:
            problems.append(f"BF {s}->100: {d} vs {ref}")
if w2["matrix"]["rows"]:
    for i in range(5):
        for j in range(5):
            d = w2["matrix"]["rows"][i][j]
            if d is None or abs(d - REF_W2_MATRIX[i][j]) > 0.0051:
                problems.append(f"matriz [{V5[i]},{V5[j]}]: {d} vs {REF_W2_MATRIX[i][j]}")
checked = w2["bellman_ford"]["status"] == "ok" and bool(w2["matrix"]["rows"])
dado("w2.check", ("conferem" if not problems else "DIVERGEM") if checked else DASH)
for p in problems:
    print("DIVERGÊNCIA W_2:", p, file=sys.stderr)

# ── trecho de relax_rounds, copiado literalmente de graph.hpp ────────────────
lines = (root / "include/cos/graph.hpp").read_text().splitlines()
i0 = next(i for i, l in enumerate(lines) if "++summary.rounds;" in l)
start = next(i for i in range(i0, len(lines)) if "for (const auto vertex : active) {" in lines[i])
end = next(i for i in range(start, len(lines)) if "// As marcas só valem" in lines[i])
block = [l for l in lines[start:end]]
while block and not block[-1].strip():
    block.pop()
indent = len(block[0]) - len(block[0].lstrip())
(here / "relax.txt").write_text("\n".join(l[indent:] for l in block) + "\n")

# Chaves usadas no .tex e ainda sem valor (benchmark em andamento) viram "---".
import re
used = set(re.findall(r"\\dado\{([^}]+)\}", (here / "relatorio.tex").read_text()))
used |= set(re.findall(r"\\dado\{([^}]+)\}", "\n".join(out)))
for key in sorted(used - set(dados)):
    if not re.match(r"^(W_\d|cmp)\.", key):
        print("aviso: chave sem valor:", key, file=sys.stderr)
    dado(key, DASH)

out.extend(f"\\expandafter\\def\\csname dado@{key}\\endcsname{{{value}}}"
           for key, value in dados.items())
(here / "tabelas.tex").write_text(
    "% Gerado por report/parte3/tabelas.py a partir de data.json; não edite à mão.\n"
    + "\n".join(out) + "\n")
print(f"tabelas.tex: {len(dados)} valores, {len(graphs)} grafos, "
      f"{len(problems)} divergências")
