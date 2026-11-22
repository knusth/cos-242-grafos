#!/usr/bin/env python3
"""Gera report/parte2/tabelas.tex a partir de report/parte2/data.json (produzido por bench/summarize.py).

Uso: python3 report/parte2/tabelas.py
O relatório só usa \\dado{chave} e as tabelas geradas aqui; nenhum número é digitado à mão.
"""
import json
import math
from pathlib import Path

here = Path(__file__).resolve().parent
data = json.loads((here / "data.json").read_text())
machine, graphs, fit, colab, low = (
    data["machine"], data["graphs"], data["fit"], data["colab"], data["lowlevel"])
k = machine["k"]
ram = machine["memory_bytes"]


# ── formatação em pt-BR ─────────────────────────────────────────────────────
def num(x, d=0):
    if x is None:
        return "---"
    s = f"{abs(x):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("$-$" if x < 0 else "") + s


def dur(s):
    if s is None:
        return "---"
    if s < 1:
        return num(s * 1000, 2 if s < 0.01 else 1) + "\\,ms"
    if s < 120:
        return num(s, 2) + "\\,s"
    if s < 7200:
        return num(s / 60, 1) + "\\,min"
    if s < 172800:
        return num(s / 3600, 1) + "\\,h"
    if s < 2 * 365 * 86400:
        return num(s / 86400, 1) + "\\,dias"
    return num(s / (365 * 86400), 1) + "\\,anos"


def dur_pm(mean, std):
    """Média ± desvio na mesma unidade e com as mesmas casas da média."""
    value, unit = dur(mean).split("\\,")
    scale = {"ms": 1e-3, "s": 1.0}.get(unit)
    if scale is None:
        return f"{dur(mean)} $\\pm$ {dur(std)}"
    places = len(value.split(",")[1]) if "," in value else 0
    return f"{value} $\\pm$ {num(std / scale, places)}\\,{unit}"


def pct(x):
    """Porcentagem com uma casa abaixo de 10%, para que 0,9% não vire 1%."""
    return num(x, 1 if x < 10 else 0) + "\\%"


def size(b):
    if b is None:
        return "---"
    for scale, unit in ((1e15, "PB"), (1e12, "TB"), (1e9, "GB")):
        if b >= 999.5 * scale / 1000:
            return num(b / scale, 1) + "\\," + unit
    return num(b / 1e6, 0) + "\\,MB"


def count(n):
    return num(n / 1e6, 1) + "\\,mi" if n >= 1e6 else num(n / 1e3, 0) + "\\,mil"


def ratio(x):
    """Acima de mil a razão vem do modelo, que não sustenta mais que dois algarismos."""
    if x >= 1000:
        x = round(x, 1 - int(math.floor(math.log10(x))))
    return ("$\\sim$" if x >= 1000 else "") + num(x) + "$\\times$"


def vec_time(g):
    return g["vector"]["mean_s"] if g["vector"] else g["vector_estimate_s"]


def heap_ns(g):
    n, m = g["vertices"], g["edges"]
    return g["heap"]["mean_s"] / ((n + m) * math.log2(n)) * 1e9


def tex(s):
    """Nome do grafo: W_3 vira W com subscrito."""
    base, _, k = s.partition("_")
    return f"\\W{{{k}}}" if base == "W" and k.isdigit() else s.replace("_", "\\_")


out = []
dados = {}


def dado(key, value):
    dados[key] = value


# ── valores avulsos usados no texto ─────────────────────────────────────────
by_name = {g["name"]: g for g in graphs}
dado("k", str(k))
dado("seed", str(machine["seed"]))
dado("cpu", machine["cpu"])
dado("ram", num(ram / 2**30) + "\\,GiB")
dado("compiler", machine["compiler"].split(" (")[0])
ghz = low["clock_ghz"]
dado("ghz", num(ghz, 2))
# Varredura: mediana dentro do L2 (n de 10^4 a 10^6), onde as curvas são planas.
def scan_mid(key):
    v = sorted(r[key] for r in low["scan"] if 1e4 <= r["n"] <= 1e6)
    return v[len(v) // 2]
scan_big = low["scan"][-1]
lib, chains, simd = scan_mid("library"), scan_mid("chains"), scan_mid("simd")
lib_all = [r["library"] for r in low["scan"]]
dado("scan.lib", num(lib, 2))
dado("scan.lib.min", num(min(lib_all), 2))
dado("scan.lib.max", num(max(lib_all), 2))
dado("scan.lib.cycles", num(lib * ghz, 1))
dado("scan.chains", num(chains, 2))
dado("scan.chains.x", num(lib / chains, 1) + "$\\times$")
dado("scan.simd", num(simd, 2))
dado("scan.simd.x", num(lib / simd, 1) + "$\\times$")
dado("scan.simd.big", num(scan_big["simd"], 2))
dado("scan.big.n", count(scan_big["n"]))
dado("scan.simd.gbs", num(8 / scan_big["simd"]))
pops = low["pops"]
pop_ns = [e["library"]["ns"] for e in pops.values()]
dado("pops.min", num(min(pop_ns), 2))
dado("pops.max", num(max(pop_ns), 2))
dado("pops.cycles", num(sum(pop_ns) / len(pop_ns) * ghz, 1))
for v in fit["validation"]:
    dado(f"val.{v['graph']}.err", num(v["error_pct"], 1) + "\\%")
    dado(f"val.{v['graph']}.runs", str(v["runs"]))
    dado(f"val.{v['graph']}.slowest", num(v["slowest_ns"] / v["measured_ns"], 1) + "$\\times$")
    dado(f"val.{v['graph']}.spread", num(100 * (v["slowest_ns"] / v["fastest_ns"] - 1)) + "\\%")
dado("pops.limit.W_7", num(pops["W_7"]["limit"]))
dado("pops.limit.W_5", num(pops["W_5"]["limit"]))


def latency(target):
    return min(low["chase"], key=lambda r: abs(math.log(r[0] / target)))[1]


dado("lat.l1", num(latency(32 * 2**10), 1))
dado("lat.l2", num(latency(4 * 2**20), 1))
dado("lat.dram", num(latency(2**30)))
layout = {(r["vertices"], r["labeling"]): r for r in low["layout"]}
layout_n = sorted({n for n, _ in layout})
for n in layout_n:
    loc, ran = layout[(n, "local")], layout[(n, "aleatoria")]
    key = f"layout.{int(round(math.log10(n)))}" if n in (1e5, 1e6, 1e7) else "layout.max"
    dado(f"{key}.local", num(loc["ns_per_op"], 2))
    dado(f"{key}.random", num(ran["ns_per_op"], 2))
    dado(f"{key}.x", num(ran["ns_per_op"] / loc["ns_per_op"], 1) + "$\\times$")
dado("layout.maxn", count(layout_n[-1]))
order = low["order"]
for name, o in order.items():
    lab = o["labelings"]
    dado(f"order.{name}.gap", num(lab["original"]["gap"], 3))
    dado(f"order.{name}.random", num(lab["aleatoria"]["gap"], 3))
    dado(f"order.{name}.bfs", num(lab["bfs"]["gap"], 3))
    dado(f"order.{name}.bfs.change",
         num(100 * (lab["bfs"]["mean_s"] / lab["original"]["mean_s"] - 1), 0) + "\\%")
    dado(f"order.{name}.random.change",
         num(100 * (lab["aleatoria"]["mean_s"] / lab["original"]["mean_s"] - 1), 0) + "\\%")
    dado(f"order.{name}.pushes", num(o["pushes"] / o["pops"], 1))
    if o.get("heap_peak"):
        dado(f"order.{name}.peak", count(o["heap_peak"]))
        dado(f"order.{name}.peak.pct", num(100 * o["heap_peak"] / o["vertices"]) + "\\%")
peaks = [r["heap_peak"] for r in low["layout"] if r.get("heap_peak")]
if peaks:
    dado("layout.peak.max", num(max(peaks)))
    dado("layout.peak.kb", num(max(peaks) * 16 / 1000) + "\\,kB")

# Contadores de hardware (bench/run_counters.sh): fração dos ciclos em que a operação de memória
# mais antiga esperava uma falta no L1.
ctr = data.get("counters") or {}


def wait_pct(e):
    return 100 * e["ciclos_espera_l1d"] / e["ciclos"]


if ctr:
    loc, ran = ctr["local_10000000/local/heap"], ctr["local_10000000/aleatoria/heap"]
    dado("ctr.layout.n", count(loc["vertices"]))
    dado("ctr.layout.instr", num(100 * abs(ran["instrucoes"] / loc["instrucoes"] - 1), 0) + "\\%")
    dado("ctr.layout.cycles.x", num(ran["ciclos"] / loc["ciclos"], 1) + "$\\times$")
    dado("ctr.layout.l1.x", num(ran["faltas_l1d"] / loc["faltas_l1d"]) + "$\\times$")
    dado("ctr.layout.tlb.x", num(ran["faltas_tlb_l2"] / loc["faltas_tlb_l2"]) + "$\\times$")
    dado("ctr.local.wait", pct(wait_pct(loc)))
    dado("ctr.random.wait", pct(wait_pct(ran)))
    vectors = [e for key, e in ctr.items() if key.endswith("/vetor")]
    dado("ctr.vec.wait", pct(max(wait_pct(e) for e in vectors)))
    dado("ctr.vec.ipc", num(sum(e["instrucoes"] / e["ciclos"] for e in vectors) / len(vectors), 1))
    dado("ctr.vec.cpe", num(sum(e["ciclos"] / (e["extracoes"] * e["vertices"]) for e in vectors)
                            / len(vectors), 1))
    for name in ("W_3", "W_4", "W_5"):
        e = ctr[f"{name}/original/heap"]
        dado(f"ctr.{name}.wait", pct(wait_pct(e)))
        dado(f"ctr.{name}.ipc", num(e["instrucoes"] / e["ciclos"], 1))
        dado(f"ctr.{name}.tlb", num(e["faltas_tlb_l2"] / e["extracoes"], 0))
    # Barras: (rótulo, execução) de cima para baixo.
    bars = [("vetor, \\W{5}", "W_5/original/vetor"),
            ("heap, local", "local_10000000/local/heap"),
            ("heap, embaralhado", "local_10000000/aleatoria/heap"),
            ("heap, \\W{3}", "W_3/original/heap"),
            ("heap, \\W{4}", "W_4/original/heap"),
            ("heap, \\W{5}", "W_5/original/heap")][::-1]
    out.append("\\pgfplotsset{contadores/.style={yticklabels={" + ",".join(
        f"{{{b}}}" for b, _ in bars) + "}}}")
    out.append("\\newcommand{\\contadoresEspera}{" + " ".join(
        f"({wait_pct(ctr[k]):.1f},{i})" for i, (_, k) in enumerate(bars)) + "}")
    out.append("\\newcommand{\\contadoresResto}{" + " ".join(
        f"({100 - wait_pct(ctr[k]):.1f},{i})" for i, (_, k) in enumerate(bars)) + "}")
    out.append("\\newcommand{\\contadoresIPC}{" + "\n".join(
        f"\\node[font=\\scriptsize, right] at (axis cs:100,{i}) "
        f"{{{num(ctr[k]['instrucoes'] / ctr[k]['ciclos'], 1)}}};" for i, (_, k) in enumerate(bars)) + "}")
    # Rótulos das barras: coordenadas marcadas dentro do eixo, nós desenhados depois dele,
    # para não ficarem sob a barra cinza.
    out.append("\\newcommand{\\contadoresMarcas}{" + "\n".join(
        f"\\coordinate (espera{i}) at (axis cs:{wait_pct(ctr[k]):.1f},{i});"
        for i, (_, k) in enumerate(bars)) + "}")
    out.append("\\newcommand{\\contadoresRotulos}{" + "\n".join(
        f"\\node[font=\\scriptsize, right, inner sep=1.5pt] at (espera{i}) "
        f"{{{pct(wait_pct(ctr[k]))}}};" for i, (_, k) in enumerate(bars)) + "}")
for g in graphs:
    n = g["name"]
    dado(f"{n}.heap", dur(g["heap"]["mean_s"]))
    dado(f"{n}.n", count(g["vertices"]))
    dado(f"{n}.heapk", dur(g["heap"]["mean_s"] * k))
    if g["vector"]:
        dado(f"{n}.vec", dur(g["vector"]["mean_s"]))
    dado(f"{n}.vecest", dur(g["vector_estimate_s"]))
    dado(f"{n}.veck", dur(g["vector_estimate_s"] * k))
    dado(f"{n}.ratio", ratio(vec_time(g) / g["heap"]["mean_s"]))
    dado(f"{n}.heapns", num(heap_ns(g), 1))
    dado(f"{n}.degree", num(2 * g["edges"] / g["vertices"], 1))
    dado(f"{n}.csr", size(g["memory_bytes"]))
    dado(f"{n}.pico", size(g["peak_rss_bytes"]))
    dado(f"{n}.matriz", size(g["matrix_bytes_estimate"]))
    if g.get("vector_variants_s"):
        dado(f"{n}.chainsest", dur(g["vector_variants_s"]["chains"]))
        dado(f"{n}.chainsratio", ratio(g["vector_variants_s"]["chains"] / g["heap"]["mean_s"]))
heap_total = sum(g["heap"]["mean_s"] * g["heap"]["runs"] for g in graphs)
vec_total = sum(g["vector"]["mean_s"] * g["vector"]["runs"] for g in graphs if g["vector"])
dado("bench.total", dur(heap_total + vec_total + colab["heap"]["mean_s"] * k))
dado("bench.W7heap", dur(graphs[-1]["heap"]["mean_s"] * graphs[-1]["heap"]["runs"]))
dado("bench.vec", dur(vec_total))
dado("heapns.growth", num(heap_ns(graphs[-1]) / heap_ns(graphs[0])) + "$\\times$")
degrees = [2 * g["edges"] / g["vertices"] for g in graphs]
dado("degree.min", num(min(degrees), 1))
dado("degree.max", num(max(degrees), 1))
dado("matrix.limit", num(math.sqrt(ram / 9) / 1000) + "\\,mil")
dado("colab.n", count(colab["vertices"]))
dado("colab.m", count(colab["edges"]))
dado("colab.source", str(colab["source"]))
dado("colab.heap", dur(colab["heap"]["mean_s"]))
dado("colab.reached", num(colab["reached_mean"] / colab["vertices"] * 100) + "\\%")



# ── caminhos nos grafos W: uma linha por caminho, em texto simples para copiar ──
rows = []
for gi, g in enumerate(graphs):
    if gi:
        rows.append("\\midrule")
    for i, p in enumerate(g["paths"]):
        name = tex(g["name"]) if i == 0 else ""
        if p["path"]:
            cells = [num(p["distance"], 2), str(len(p["path"]) - 1), " ".join(str(x) for x in p["path"])]
        else:
            cells = ["$\\infty$", "---", "inalcançável"]
        rows.append(f"{name} & {p['target']} & " + " & ".join(cells) + "\\\\")
out.append("\\newcommand{\\tabelaCaminhos}{" + "\n".join(rows) + "}")

# ── tabela de tempos ────────────────────────────────────────────────────────
rows = []
for g in graphs:
    vec = g["vector"]
    vector = dur(vec["mean_s"]) if vec else f"\\textit{{{dur(g['vector_estimate_s'])}}}"
    rows.append(" & ".join([
        tex(g["name"]), count(g["vertices"]), count(g["edges"]),
        num(2 * g["edges"] / g["vertices"], 1),
        dur_pm(g["heap"]["mean_s"], g["heap"]["std_s"]),
        vector, ratio(vec_time(g) / g["heap"]["mean_s"]), num(heap_ns(g), 1),
    ]) + "\\\\")
out.append("\\newcommand{\\tabelaTempos}{" + "\n".join(rows) + "}")

# ── figuras ─────────────────────────────────────────────────────────────────
# Baixo nível: latência de uma leitura dependente.
out.append("\\newcommand{\\latencia}{" + " ".join(f"({b},{ns})" for b, ns in low["chase"]) + "}")
# Marcas no eixo da latência: tamanho do vetor de distâncias (8n bytes) de cada grafo W.
marks = {}
for g in graphs:
    marks.setdefault(8 * g["vertices"], []).append(tex(g["name"]))
out.append("\\newcommand{\\marcasW}{" + "\n".join(
    f"\\draw (axis cs:{b},0.7) -- (axis cs:{b},0.85) node[above, font=\\tiny, inner sep=1pt] "
    f"{{{', '.join(names)}}};" for b, names in sorted(marks.items())) + "}")

# Tempos por origem (escala log): heap, vetor medido e vetor projetado; razão sobre as barras.
coords = lambda pts: " ".join(f"({x},{y:.6g})" for x, y in pts)
out.append("\\pgfplotsset{grafosW/.style={symbolic x coords={" +
           ",".join(g["name"] for g in graphs) + "}, xticklabels={" +
           ",".join(tex(g["name"]) for g in graphs) + "}}}")
out.append("\\newcommand{\\barrasHeap}{" + coords(
    (g["name"], g["heap"]["mean_s"]) for g in graphs) + "}")
out.append("\\newcommand{\\barrasVetor}{" + coords(
    (g["name"], g["vector"]["mean_s"]) for g in graphs if g["vector"]) + "}")
out.append("\\newcommand{\\barrasVetorProj}{" + coords(
    (g["name"], g["vector_estimate_s"]) for g in graphs if not g["vector"]) + "}")
out.append("\\newcommand{\\razoesW}{" + "\n".join(
    f"\\node[font=\\scriptsize, above, inner sep=2pt] at (axis cs:{g['name']},{vec_time(g):.6g}) "
    f"[xshift=5pt] {{{ratio(vec_time(g) / g['heap']['mean_s'])}}};" for g in graphs) + "}")

# Escala: tempo do heap contra (n+m)log2 n, e reta de inclinação 1 pelo W_3.
ops = lambda g: (g["vertices"] + g["edges"]) * math.log2(g["vertices"])
out.append("\\newcommand{\\pontosEscala}{" + coords((ops(g), g["heap"]["mean_s"]) for g in graphs) + "}")
g0 = graphs[0]
out.append("\\newcommand{\\retaEscala}{" + coords(
    (x, g0["heap"]["mean_s"] * x / ops(g0)) for x in (ops(g0) / 2, ops(graphs[-1]) * 2)) + "}")
out.append("\\newcommand{\\rotulosEscala}{" + "\n".join(
    f"\\node[font=\\scriptsize, anchor=north west, inner sep=2pt] at (axis cs:{ops(g):.6g},{g['heap']['mean_s']:.6g}) {{{tex(g['name'])}}};"
    for g in graphs) + "}")
# Vetor: tempo por posição percorrida numa extração, contra n.
out.append("\\newcommand{\\pontosVetorPos}{" + coords(
    (by_name[name]["vertices"], ns) for name, ns in fit["ns_per_estimate"].items()) + "}")

# Contagens do heap (bench/contagem_heap.cpp): atualizações de dist e tamanho do heap.
cont = json.loads((here / "contagens.json").read_text())
cg = cont["graphs"]
dado("cont.origins", str(cont["origins"]))
for name, c in cg.items():
    dado(f"{name}.upd", num(c["pushes"] / c["n"], 1))
    dado(f"{name}.updpct", num(100 * c["pushes"] / c["m"]) + "\\%")
    dado(f"{name}.peakpct", num(100 * c["peak"] / c["n"]) + "\\%")
out.append("\\newcommand{\\pontosAtualizacoes}{" + coords(
    (2 * c["m"] / c["n"], c["pushes"] / c["n"]) for c in cg.values()) + "}")
out.append("\\newcommand{\\rotulosAtualizacoes}{" + "\n".join(
    f"\\node[font=\\scriptsize, anchor=north west, inner sep=2pt] at (axis cs:{2 * c['m'] / c['n']:.6g},{c['pushes'] / c['n']:.6g}) {{{tex(name)}}};"
    for name, c in cg.items()) + "}")
for name, c in cg.items():
    out.append(f"\\expandafter\\def\\csname heapTam@{name}\\endcsname{{" + coords(
        (i / c["n"], size / c["n"]) for i, size, _ in c["trace"]) + "}")

# Rede de colaboração: vértices alcançados e tempo de cada origem.
runs = colab["runs"]
giant = max(r for r, _ in runs)
in_giant = [t for r, t in runs if r == giant]
dado("colab.giant", num(giant))
dado("colab.giant.pct", num(100 * giant / colab["vertices"]) + "\\%")
dado("colab.giant.runs", str(len(in_giant)))
dado("colab.small.runs", str(len(runs) - len(in_giant)))
dado("colab.small.max", str(max(r for r, _ in runs if r != giant)))
dado("colab.giant.heap", dur(sum(in_giant) / len(in_giant)))
dado("colab.amdahl", num(colab["vertices"] / giant, 2) + "$\\times$")

# Árvore dos caminhos mínimos a partir de Dijkstra: prefixos comuns viram um só nó.
found = sorted((p for p in colab["paths"] if p.get("path_names") and p.get("edge_weights")),
               key=lambda p: p["path_names"])  # prefixos comuns ficam vizinhos, sem cruzamentos
children, weight_in, depth, leaves = {}, {}, {}, []
for p in found:
    names, ws = p["path_names"], p["edge_weights"]
    for i, name in enumerate(names):
        depth[name] = i
        if i:
            children.setdefault(names[i - 1], [])
            if name not in children[names[i - 1]]:
                children[names[i - 1]].append(name)
            weight_in[name] = ws[i - 1]
    leaves.append(names[-1])
column = {leaf: i for i, leaf in enumerate(leaves)}


def place(name):
    if name not in children:
        return column[name]
    xs = [place(c) for c in children[name]]
    column[name] = sum(xs) / len(xs)
    return column[name]


root = found[0]["path_names"][0]
place(root)
lines = []
ids = {name: f"n{i}" for i, name in enumerate(column)}
total = {root: 0.0}
for name in sorted(column, key=lambda n: depth[n]):
    leaf = name not in children
    # A folha tem duas linhas: desce um pouco para o peso da aresta não encostar na caixa.
    x, y = column[name] * 4.2, -depth[name] * 0.92 - (0.22 if leaf else 0)
    if name != root:
        parent = next(a for a, cs in children.items() if name in cs)
        total[name] = total[parent] + weight_in[name]
    label = name + (f"\\\\\\textbf{{{num(total[name], 2)}}}" if leaf else "")
    style = "folha" if leaf else ("raiz" if name == root else "pessoa")
    lines.append(f"\\node[{style}] ({ids[name]}) at ({x:.2f},{y:.2f}) {{{label}}};")
for parent, cs in children.items():
    for c in cs:
        w = weight_in[c]
        style = "caro" if w >= 0.999 else "barato"
        lines.append(f"\\draw[{style}] ({ids[parent]}) -- node[peso] {{{num(w, 2)}}} ({ids[c]});")
out.append("\\newcommand{\\arvoreColab}{" + "\n".join(lines) + "}")
for key, pat in (("kleinberg", "Kleinberg"), ("kruskal", "Kruskal"), ("tardos", "Tardos"),
                 ("figueiredo", "Figueiredo")):
    p = next(q for q in found if pat in q["name"])
    dado(f"colab.{key}.d", num(p["distance"], 2))
    dado(f"colab.{key}.hops", str(len(p["path_names"]) - 1))
first_two = {p["name"]: sum(p["edge_weights"][:2]) / p["distance"] for p in found}
dado("colab.firsttwo.kleinberg", num(100 * first_two["Jon M. Kleinberg"]) + "\\%")

# Tabela compacta de distâncias (destinos nas linhas, grafos nas colunas).
targets = [p["target"] for p in graphs[0]["paths"]]
rows = []
for i, t in enumerate(targets):
    cells = []
    for g in graphs:
        p = g["paths"][i]
        cells.append(f"{num(p['distance'], 2)} & {len(p['path']) - 1}" if p["path"] else "$\\infty$ & ---")
    rows.append(f"{t} & " + " & ".join(cells) + "\\\\")
out.append("\\newcommand{\\tabelaDistancias}{" + "\n".join(rows) + "}")
for g in graphs:
    found_w = [p for p in g["paths"] if p["path"]]
    ds, hs = [p["distance"] for p in found_w], [len(p["path"]) - 1 for p in found_w]
    dado(f"{g['name']}.dmin", num(min(ds), 2))
    dado(f"{g['name']}.dmax", num(max(ds), 2))
    dado(f"{g['name']}.hmin", str(min(hs)))
    dado(f"{g['name']}.hmax", str(max(hs)))

out.extend(f"\\expandafter\\def\\csname dado@{key}\\endcsname{{{value}}}"
           for key, value in dados.items())

(here / "tabelas.tex").write_text(
    "% Gerado por report/parte2/tabelas.py a partir de data.json; não edite à mão.\n"
    + "\n".join(out) + "\n")
print(f"tabelas.tex: {len(dados)} valores, {len(graphs)} grafos")
