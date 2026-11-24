#!/usr/bin/env python3
"""Gera report/parte3/tabelas.tex a partir de data.json, contagens.json e exemplo.json.

Uso: python3 -I report/parte3/tabelas.py
  data.json      bench/summarize_p3.py (tempos, distâncias, matrizes)
  contagens.json bench/contagem_bf.cpp (ativos e arestas examinadas por rodada)
  grafos.json    grafos.py (grau, pesos, saltos até o 100, corte em faixas)
  tempo_busca_ciclo.json, bench/results/parte3/*.txt (Johnson, threads)
  exemplo.json   grafo pequeno do exemplo (CSR, rodadas do Bellman-Ford)
O relatório só usa \\dado{chave}, as tabelas e as figuras geradas aqui; nenhum número do texto é
digitado à mão. Valores ausentes viram "---".
"""
import json
import math
import re
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
data = json.loads((here / "data.json").read_text())
cont = json.loads((here / "contagens.json").read_text())
import os
w1c = json.loads((here / "w1_ciclos.json").read_text())
ex = json.loads(Path(os.environ.get("EXEMPLO", here / "exemplo.json")).read_text())
machine, graphs = data["machine"], data["graphs"]
by = {g["name"]: g for g in graphs}
cby = {g["nome"]: g for g in cont["grafos"]}

# Conferência independente do W_2 (Dijkstra em Python, feito à parte).
REF_W2_BF = {"10": 10.47, "20": 8.48, "30": 8.71}
REF_W2_MATRIX = [[0, 11.73, 8.14, 9.49, 7.08], [3.84, 0, 7.03, 8.3, 4.7],
                 [5.79, 12.55, 0, 8.3, 6.33], [5.05, 12.32, 5.36, 0, 5.71],
                 [4.48, 12.23, 7.79, 8.26, 0]]
# Verificações de tests/graph_tests.cpp (execução registrada, não recalculada aqui).
TEST_CHECKS = 55823939
DASH = "---"
RAM_GIB = 36
# BF todos-pares do W_2 em 1 thread, extrapolado de 2000 destinos.
REF_W2_1THREAD_S = float(re.search(
    r"media_s=([0-9.eE+-]+)",
    (here.parent.parent / "bench/results/parte3/p3_W_2.bf_1thread_amostra.txt").read_text()).group(1))


# ── formatação em pt-BR ─────────────────────────────────────────────────────
def num(x, d=0):
    if x is None:
        return DASH
    s = f"{abs(x):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("$-$" if x < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else "") + s


def sig(x, n=2):
    """Número com n algarismos significativos."""
    if x == 0:
        return "0"
    d = n - 1 - int(math.floor(math.log10(abs(x))))
    return num(round(x, d), max(d, 0))


def unit_split(s):
    for lim, scale, unit in ((1e-3, 1e-6, "\\textmu s"), (1, 1e-3, "ms"), (120, 1, "s"),
                             (7200, 60, "min"), (172800, 3600, "h"),
                             (330 * 86400, 86400, "dias"),
                             (float("inf"), 365 * 86400, "anos")):
        if s < lim:
            return scale, unit


def dur(s, n=3):
    """Duração com n algarismos significativos (3 nas tabelas, 2 no texto)."""
    if s is None:
        return DASH
    scale, unit = unit_split(s)
    return sig(s / scale, n) + "\\," + unit


def dur_pm(mean, std):
    """Média ± desvio, na unidade da média e com as mesmas casas."""
    if mean is None or std is None:
        return dur(mean)
    scale, unit = unit_split(mean)
    value = sig(mean / scale, 3)
    places = len(value.split(",")[1]) if "," in value else 0
    return f"{value} $\\pm$ {num(std / scale, places)}\\,{unit}"


def size(b, n=2):
    if b is None:
        return DASH
    for scale, unit in ((1e15, "PB"), (1e12, "TB"), (1e9, "GB")):
        if b >= scale:
            return sig(b / scale, n) + "\\," + unit
    return sig(b / 1e6, n) + "\\,MB"


def sci(x):
    if x is None:
        return DASH
    e = int(math.floor(math.log10(x)))
    if round(x / 10 ** e, 1) == 1.0:
        return f"$10^{{{e}}}$"
    return f"${num(x / 10 ** e, 1).replace(',', '{,}')}\\cdot10^{{{e}}}$"


def big(x):
    """Contagem em prosa: 2,8 milhões, 620 milhões, 1,2 bilhão."""
    if x < 1e6:
        return sig(x)
    if x < 1e9:
        return sig(x / 1e6) + " milhões"
    if x < 1e12:
        return sig(x / 1e9) + " bilhões"
    return sci(x)


def p10(x):
    e = int(math.floor(math.log10(x)))
    m = x / 10 ** e
    if round(m, 1) == 1.0:
        return f"10^{{{e}}}"
    return f"{num(m, 2 if m < 9.995 else 1).replace(',', '{,}')}\\cdot10^{{{e}}}"


def times(x, n=2):
    return DASH if x is None else sig(x, n) + "\\,$\\times$"


def tex(name):
    return f"\\W{{{name.partition('_')[2]}}}"


def mil(v):
    return f"{v // 1000} mil" if v % 1000 == 0 and v >= 1000 else num(v)


dados = {}


def dado(key, value):
    dados[key] = value


out = []

# ── máquina e dados gerais ───────────────────────────────────────────────────
dado("cpu", machine["cpu"] or DASH)
dado("ram", num(machine["memory_bytes"] / 2**30) + "\\,GiB")
dado("threads", str(machine["threads"]))
dado("compiler", (machine["compiler"] or DASH).split(" (")[0])
limit = next((g["floyd_warshall"]["limit_gib"] for g in graphs
              if g["floyd_warshall"]["limit_gib"]), None)
dado("w1.cic", num(w1c["ciclos_negativos_2"]))

fw_ref = next(g for g in graphs if g["floyd_warshall"]["status"] == "ok")
fw_ref_t = fw_ref["floyd_warshall"]["mean_s"]
fw_ref_threads = fw_ref["floyd_warshall"]["threads"]


def fw_time(g):
    """(tempo, estimado?) do Floyd-Warshall; a estimativa escala o do grafo de referência por V^3."""
    fw = g["floyd_warshall"]
    if fw["status"] == "ok":
        return fw["mean_s"], False
    if fw["status"] == "memoria_insuficiente":
        return fw_ref_t * (g["vertices"] / fw_ref["vertices"]) ** 3, True
    return None, False


for g in graphs:
    n, V, E = g["name"], g["vertices"], g["edges"]
    bf, fw, ap, c = g["bellman_ford"], g["floyd_warshall"], g["all_pairs_bf"], cby[n]
    dado(f"{n}.V", num(V))
    dado(f"{n}.E", num(E))
    dado(f"{n}.deg", num(E / V, 0))
    dado(f"{n}.csrmem", size(g["graph_memory_bytes"], 3))
    dado(f"{n}.fwmem", size(fw["memory_needed_bytes"]))
    dado(f"{n}.bf.rounds", num(bf["rounds"]))
    dado(f"{n}.bf1", dur(bf["mean_s"], 2 if bf["mean_s"] < 1e-3 else 3))
    dado(f"{n}.ap.sample", num(ap["sample"]))
    dado(f"{n}.ap", dur(ap["mean_s"], 2))
    t_fw, est = fw_time(g)
    dado(f"{n}.fw", dur(t_fw if t_fw is not None else fw["mean_s"], 2))
    if bf["status"] == "ok":
        # Razão FW/BF com os mesmos núcleos: o BF estimado usa 1 thread, o FW usa 11.
        nthr = (fw["threads"] or fw_ref_threads)
        ratio = t_fw / (ap["mean_s"] * (ap["threads"] or 1) / nthr)
        dado(f"{n}.ratio", times(ratio))
        g["_ratio"] = ratio
    first = c["rodadas"][0]
    ativos = [r["ativos"] for r in c["rodadas"]]
    pico = max(range(len(ativos)), key=lambda i: ativos[i])

ok = [g for g in graphs if g["bellman_ford"]["status"] == "ok"]
# ── todos os pares: contagens por destino, ns por operação ────────────────────
for g in ok:
    n, V, E = g["name"], g["vertices"], g["edges"]
    a = cby[n]["todos_os_pares"]
    dado(f"{n}.rmed", num(a["rodadas_media"], 0))
    dado(f"{n}.pass", num(a["passagens_por_E_media"], 1))
    dado(f"{n}.vm1", num(V - 1))
    dado(f"{n}.opsratio", sig(V * V / a["arestas_examinadas_media"], 2))
    dado(f"{n}.exdest", big(a["arestas_examinadas_media"]))
w2, ap2 = by["W_2"], by["W_2"]["all_pairs_bf"]
a2 = cby["W_2"]["todos_os_pares"]
dado("ns.bf1", num(REF_W2_1THREAD_S / a2["arestas_examinadas_total_extrapolado"] * 1e9, 1))
dado("V3", sci(w2["vertices"] ** 3))
_t = (here.parent.parent / "bench/results/parte3/fw_aleatorio5000_1thread.txt").read_text()
_fw5 = {"1": float(re.search(r"\[floyd_warshall\].*?media_s=([0-9.eE+-]+)", _t, re.S).group(1))}
_V5k = int(re.search(r"vertices=(\d+)", _t).group(1))
assert _V5k == int(re.search(r"vertices=(\d+)", (here.parent.parent / "bench/results/parte3/escala_aleatorio5000_t1.txt").read_text()).group(1))
_ns_fw1 = _fw5["1"] / _V5k ** 3 * 1e9
_ns_bf1 = REF_W2_1THREAD_S / a2["arestas_examinadas_total_extrapolado"] * 1e9
dado("fw5k.V", num(_V5k))
dado("ns.fw1", num(_ns_fw1, 2))
dado("ns.mem", num(round(_ns_bf1 / _ns_fw1), 0))
dado("noearly", sci((by["W_2"]["vertices"] - 1) * by["W_2"]["edges"]))
dado("exall", sci(a2["arestas_examinadas_total_extrapolado"]))

# Cadeia de fatores do §4.4 (a mesma do slide 6): (V−1)·E ÷ V² → parada antecipada → lista de ativos
# → custo por relaxação deduzido no W_2 (tempo × threads ÷ relaxações, mesma sessão) → razão medida.
_V2, _E2 = w2["vertices"], w2["edges"]
_bf_s, _fw_s = ap2["mean_s"], w2["floyd_warshall"]["mean_s"]
_bf_ops = a2["arestas_examinadas_total_extrapolado"]
_f_pred = (_V2 - 1) * _E2 / _V2 ** 2
_f_par = (_V2 - 1) / a2["rodadas_media"]
_f_at = a2["rodadas_media"] * _E2 / a2["arestas_examinadas_media"]
_f_rel = a2["arestas_examinadas_media"] / _V2 ** 2
_ns_bf11 = _bf_s * ap2["threads"] / _bf_ops * 1e9
_ns_fw11 = _fw_s * w2["floyd_warshall"]["threads"] / _V2 ** 3 * 1e9
_f_med = _bf_s / _fw_s
assert abs(_f_pred / _f_par / _f_at - _f_rel) < 1e-9 * _f_rel
assert abs(_f_rel * _ns_bf11 / _ns_fw11 - _f_med) < 0.01 * _f_med


def fracao(v):
    return sig(v, 2) + "\\,$\\times$" if v >= 1 else f"1/{sig(1 / v, 2 if 1 / v < 100 else 3)}"


dado("f.pred", sig(_f_pred, 2))
dado("f.par", num(_f_par))
dado("f.at", num(_f_at, 2))
dado("f.rel", fracao(_f_rel))
dado("f.custo", sig(_ns_bf11 / _ns_fw11, 2))
dado("f.med", fracao(_f_med))
dado("ns.bf11", sig(_ns_bf11, 2))
dado("ns.fw11", sig(_ns_fw11, 2))
dado("W_2.rmed1", num(a2["rodadas_media"], 1))

tb = {g["nome"]: g for g in json.loads((here / "tempo_busca_ciclo.json").read_text())["grafos"]}
dado("prof.min", num(tb["W_2"]["profundidade_arvore"]))
dado("prof.max", num(tb["W_5"]["profundidade_arvore"]))
dado("fw.limit", num(limit, 0) + "\\,GiB")
dado("W_2.ap1t", num(REF_W2_1THREAD_S, 1) + "\\,s")
dado("busca.w5.pct", num(tb["W_5"]["fracao_busca"] * 100, 1) + "\\,\\%")
dado("busca.w5.s", num(tb["W_5"]["busca_s"]["min"], 2) + "\\,s")
dado("busca.w5.tot", num(tb["W_5"]["completo_s"]["min"], 2) + "\\,s")
dado("busca.w24.min", num(min(tb[k]["fracao_busca"] for k in ("W_2", "W_3", "W_4")) * 100, 1) + "\\,\\%")
dado("busca.w24.max", num(max(tb[k]["fracao_busca"] for k in ("W_2", "W_3", "W_4")) * 100, 1) + "\\,\\%")
dado("nsa.ratio", times(tb["W_5"]["ns_por_aresta_sem_busca"] / tb["W_2"]["ns_por_aresta_sem_busca"], 3))
dado("fw.gops", num(_V2 ** 3 / _fw_s / 1e9, 1))
dado("fw.ps", num(_fw_s / _V2 ** 3 * 1e12, 0))
dado("test.checks", sig(TEST_CHECKS / 1e6, 3) + " milhões")
out.append("\\newcommand{\\serCacheNs}{" + " ".join(
    f"({i},{tb[k]['ns_por_aresta_sem_busca']:.2f})" for i, k in enumerate(("W_2", "W_3", "W_4", "W_5"), 1)) + "}")
out.append("\\newcommand{\\serCacheBusca}{" + " ".join(
    f"({i},{tb[k]['fracao_busca'] * 100:.1f})" for i, k in enumerate(("W_2", "W_3", "W_4", "W_5"), 1)) + "}")
_w2p = max(cby["W_2"]["rodadas"], key=lambda r: r["ativos"])
dado("w2.pico.pct", num(_w2p["ativos"] / by["W_2"]["vertices"] * 100, 0) + "\\,\\%")
dado("w2.pico.rod", str(_w2p["rodada"]))

# ── tabela 1: grafos ─────────────────────────────────────────────────────────
gj = {g["nome"]: g for g in json.loads((here / "grafos.json").read_text())["grafos"]}


def minus(x):
    return num(x) if x >= 0 else "$-$" + num(-x)


rows = []
for g in graphs:
    n = g["name"]
    q = gj[n]
    assert q["V"] == g["vertices"] and q["E"] == g["edges"], n
    dado(f"{n}.grau", f"{num(q['grau_saida']['media'])} ({q['grau_saida']['min']}--{q['grau_saida']['max']})")
    pw = f"{minus(q['pesos']['min'])} a {num(q['pesos']['max'])}"
    dado(f"{n}.pesos", "\\textcolor{ruim}{" + pw + "}" if q["pesos"]["negativos"] else pw)
    dado(f"{n}.saltos", num(q["saltos_ate_100"]))
    fits = g["floyd_warshall"]["memory_needed_gib"] <= RAM_GIB
    mem = f"\\dado{{{n}.fwmem}}" + ("" if fits else "\\ (não cabe)")
    rows.append(" & ".join([tex(n), f"\\dado{{{n}.V}}", f"\\dado{{{n}.E}}", f"\\dado{{{n}.grau}}",
                            f"\\dado{{{n}.pesos}}", f"\\dado{{{n}.saltos}}", mem]) + "\\\\")
out.append("\\newcommand{\\tabelaGrafos}{" + "\n".join(rows) + "}")
assert all(q["fortemente_conexo"] for q in gj.values())
dado("w1.recip", num(gj["W_1"]["reciprocidade"] * 100) + "\\,\\%")
dado("w1.neg", num(gj["W_1"]["pesos"]["negativos"]))
dado("gap", num(sum(q["gap_medio_sobre_V"] for q in gj.values()) / 5, 2))
_cut = sum(q["corte_11_faixas"] for q in gj.values()) / 5
dado("corte", num(_cut * 100) + "\\,\\%")
dado("corte.acaso", num(10 / 11 * 100) + "\\,\\%")
dado("saltos.max13", num(max(gj[f"W_{i}"]["saltos_ate_100"] for i in (1, 2, 3))))
dado("prof.w2", num(tb["W_2"]["profundidade_arvore"]))
for _n in ("W_2", "W_3", "W_4", "W_5"):
    dado(f"nsa.{_n}", num(tb[_n]["ns_por_aresta_sem_busca"], 1))

# ── threads ──────────────────────────────────────────────────────────────────
_esc = {}
for _th in (1, 2, 3, 4, 5, 6, 8, 11):
    _t = (here.parent.parent / f"bench/results/parte3/escala_aleatorio5000_t{_th}.txt").read_text()
    _esc[_th] = tuple(float(re.search(r"\[" + sec + r"\].*?media_s=([0-9.eE+-]+)", _t, re.S).group(1))
                      for sec in ("bellman_ford_todos_pares", "floyd_warshall", "johnson"))


def ganho(th, i):
    return _esc[1][i] / _esc[th][i]


TS = (1, 2, 5, 11)
for _i, _nm in enumerate(("bf", "fw", "jo")):
    dado(f"thr5.{_nm}", num(ganho(5, _i), 1) + "\\,$\\times$")
_rows = []
for _i, _nm in enumerate(("Bellman-Ford", "Floyd-Warshall", "Johnson (radix)")):
    _rows.append(" & ".join([_nm] + [num(ganho(th, _i), 1) for th in TS]) + "\\\\")
out.append("\\newcommand{\\tabelaThreads}{" + "\n".join(_rows) + "}")
out.append("\\newcommand{\\threadsCab}{" + " & ".join(str(th) for th in TS) + "}")

# Bellman-Ford todos-pares nos grafos do estudo, amostra de destinos: a melhor execução de cada ponto.
_res = here.parent.parent / "bench/results/parte3"
_maq = dict(l.split("=", 1) for l in (_res / "maquina.txt").read_text().splitlines() if "=" in l)
NP, NE = int(_maq["nucleos_desempenho"]), int(_maq["nucleos_eficiencia"])
assert NP + NE == machine["threads"]
_L2 = int(_maq["l2_desempenho_bytes"])


def execucoes(arq, secao):
    t = (_res / arq).read_text()
    t = t[t.index(f"[{secao}]"):]
    t = t[:t.index("\n[", 1)] if "\n[" in t[1:] else t
    return [float(m.group(1)) for m in re.finditer(r"^\d+,([0-9.eE+-]+),", t, re.M)]


def mbytes(b):
    x = b / 1e6
    return num(x, 1 if x < 1 else 0) + "\\,MB"


_rows, _nruns = [], set()
for _n in ("W_2", "W_4", "W_5"):
    _runs = {th: execucoes(f"escala_{_n}_amostra_t{th}.txt", "bellman_ford_todos_pares") for th in TS}
    _nruns |= {len(r) for r in _runs.values()}
    _best = {th: min(r) for th, r in _runs.items()}
    _g = {th: _best[1] / _best[th] for th in TS}
    _K = int(re.search(r"destinos_medidos=(\d+)", (_res / f"escala_{_n}_amostra_t1.txt").read_text()).group(1))
    _ws = 12 * by[_n]["vertices"]          # dist (8 B) + next (4 B) por thread
    for th in (5, 11):
        dado(f"esc.{_n}.{th}", num(_g[th], 1) + "\\,$\\times$")
    _rows.append(" & ".join([tex(_n), mbytes(_ws), num(_K)] + [num(_g[th], 1) for th in TS]) + "\\\\")
out.append("\\newcommand{\\tabelaThreadsW}{" + "\n".join(_rows) + "}")
dado("esc.nruns", " ou ".join(str(x) for x in sorted(_nruns)))
dado("np", str(NP))
dado("ne", str(NE))
dado("l2", num(_L2 / 2 ** 20) + "\\,MiB")
dado("l2.np.W_4", mbytes(NP * 12 * by["W_4"]["vertices"]))
_nuc = dict(l.split("=", 1) for l in (_res / "nucleo_eficiencia.txt").read_text().splitlines()
            if "=" in l and not l.startswith("#"))
_r = float(_nuc["tempo_p_s"]) / float(_nuc["tempo_e_s"])
dado("nuc.r", num(_r, 2))
dado("nuc.cap", num(NP + NE * _r, 1))

# Floyd-Warshall: blocos de fw_block valores de k, barreiras contadas no código.
_hpp = (here.parent.parent / "include/cos/graph.hpp").read_text()
_fwb = int(re.search(r"fw_block\s*=\s*(\d+);", _hpp).group(1))
_i0 = _hpp.index("static bool blocked_floyd_warshall")
_nbar = _hpp[_i0:_hpp.index("return stop;", _i0)].count("sync.arrive_and_wait()")
assert _nbar == 3, _nbar
dado("fw.bloco", str(_fwb))
dado("fw.nbar", str(_nbar))
dado("fw.bar.W_2", num(_nbar * -(-w2["vertices"] // _fwb)))

# ── Johnson no W_2 (sessão separada, máquina ociosa) ─────────────────────────
_bdir = here.parent.parent / "bench/results/parte3"


def _media(arq, secao):
    t = (_bdir / arq).read_text()
    m = re.search(r"\[" + secao + r"\].*?media_s=([0-9.eE+-]+)\s+desvio_s=([0-9.eE+-]+)", t, re.S)
    return float(m.group(1)), float(m.group(2))


_jbf = _media("p3_W_2.bf_todos.txt", "bellman_ford_todos_pares")
_jh = _media("p3_W_2.johnson_heap.txt", "johnson")
_jr = _media("p3_W_2.johnson_radix.txt", "johnson")
dado("jo.bf", dur_pm(*_jbf))
dado("jo.heap", dur_pm(*_jh))
dado("jo.radix", dur_pm(*_jr).replace("0,0\\,", "0,02\\,") if round(_jr[1], 1) == 0 else dur_pm(*_jr))
dado("jo.gheap", num(_jbf[0] / _jh[0], 1) + "\\,$\\times$")
dado("jo.gradix", num(_jbf[0] / _jr[0], 1) + "\\,$\\times$")
dado("jo.fwratio", times(_fw_s / _jr[0], 2))
_nex = {len(execucoes(arq, sec)) for arq, sec in (("p3_W_2.bf_todos.txt", "bellman_ford_todos_pares"),
        ("p3_W_2.johnson_heap.txt", "johnson"), ("p3_W_2.johnson_radix.txt", "johnson"))}
assert len(_nex) == 1
dado("jo.nexec", str(_nex.pop()))

# Relaxações e custo por relaxação (tempo × threads ÷ relaxações): Bellman-Ford 3,6·V·E, Johnson V·E.
_VE = _V2 * _E2
_thr = {arq: int(re.search(r"\[(?:johnson|bellman_ford_todos_pares)\].*?threads=(\d+)", (_bdir / arq).read_text(),
                           re.S).group(1))
        for arq in ("p3_W_2.bf_todos.txt", "p3_W_2.johnson_heap.txt", "p3_W_2.johnson_radix.txt")}
_ns_b = _jbf[0] * _thr["p3_W_2.bf_todos.txt"] / _bf_ops * 1e9
_ns_h = _jh[0] * _thr["p3_W_2.johnson_heap.txt"] / _VE * 1e9
_ns_r = _jr[0] * _thr["p3_W_2.johnson_radix.txt"] / _VE * 1e9
_pas = _bf_ops / _VE
assert abs(_pas - a2["passagens_por_E_media"]) < 1e-3 * _pas
assert abs(_pas / (_ns_h / _ns_b) - _jbf[0] / _jh[0]) < 1e-6 and abs(_pas / (_ns_r / _ns_b) - _jbf[0] / _jr[0]) < 1e-6
dado("jns.hb", num(_ns_h / _ns_b, 1))
dado("jns.rb", num(_ns_r / _ns_b, 1))
dado("jo.pas", num(_pas, 1))


def dado_get(k):
    return dados[k]


_rows = [
    ("Floyd-Warshall", "$\\Theta(V^3)$", _V2 ** 3, f"{sig(_fw_s, 3)} $\\pm$ {num(w2['floyd_warshall']['std_s'])}\\,s\\textsuperscript{{$\\dagger$}}", _ns_fw11),
    ("Bellman-Ford, todos os pares", "$O(V\\cdot R\\cdot E)$", _bf_ops, dado_get("jo.bf"), _ns_b),
    ("Johnson, heap binário", "$O(V\\cdot E\\log V)$", _VE, dado_get("jo.heap"), _ns_h),
    ("Johnson, radix", "$O(V\\cdot E+V^2\\log C)$", _VE, dado_get("jo.radix"), _ns_r),
]
out.append("\\newcommand{\\tabelaComplex}{" + "\n".join(
    f"{a} & {c} & ${p10(r)}$ & {t} & {num(ns, 2 if ns < 1 else 1)}\\\\" for a, c, r, t, ns in _rows) + "}")

# Exemplo de 3 vértices do Johnson (slides 7 e 8): Dijkstra falha, constante inverte, potencial mantém.
TRI = {("A", "B"): 2, ("B", "C"): -2, ("A", "C"): 1}
TRI_K = 2


def _cam(p, c):
    return sum(p[(x, y)] for x, y in zip(c, c[1:]))


def _dij(p, s="A"):
    d, fech = {s: 0}, []
    while len(fech) < 3:
        u = min((v for v in d if v not in fech), key=d.get)
        fech.append(u)
        for (x, y), w_ in p.items():
            if x == u and y not in fech and d[u] + w_ < d.get(y, math.inf):
                d[y] = d[u] + w_
    return d


_h = {v: 0 for v in "ABC"}                     # distância até um vértice virtual q (arestas v→q de peso 0)
for _ in range(3):
    for (x, y), w_ in TRI.items():
        _h[x] = min(_h[x], w_ + _h[y])
_trik = {e: w_ + TRI_K for e, w_ in TRI.items()}
_trih = {(x, y): w_ + _h[y] - _h[x] for (x, y), w_ in TRI.items()}
assert _dij(TRI)["C"] == 1 and _cam(TRI, "ABC") == 0
assert _cam(_trik, "ABC") > _cam(_trik, "AC") and _cam(_trih, "ABC") < _cam(_trih, "AC")
assert all(w_ >= 0 for w_ in _trih.values())
dado("jx.ab", minus(TRI[("A", "B")]))
dado("jx.bc", minus(TRI[("B", "C")]))
dado("jx.ac", minus(TRI[("A", "C")]))
dado("jx.dijC", minus(_dij(TRI)["C"]))
dado("jx.abc", minus(_cam(TRI, "ABC")))
dado("jx.k", minus(TRI_K))
dado("jx.abck", minus(_cam(_trik, "ABC")))
dado("jx.ack", minus(_cam(_trik, "AC")))
for _v in "ABC":
    dado(f"jx.h{_v}", minus(_h[_v]))
dado("jx.w", ", ".join(minus(_trih[e]) for e in (("A", "B"), ("B", "C"), ("A", "C"))))

# ── distâncias até o vértice 100 ─────────────────────────────────────────────
rows = []
for s in ("10", "20", "30"):
    cells = []
    for g in graphs:
        bf = g["bellman_ford"]
        if bf["status"] == "ciclo_negativo":
            cells.append("\\textcolor{ruim}{$-\\infty$}")
        else:
            d = bf["distances"][s]
            cells.append(num(d, 2) if d is not None else "$\\infty$")
    rows.append(f"{s} & " + " & ".join(cells) + "\\\\")
out.append("\\newcommand{\\tabelaDistancias}{" + "\n".join(rows) + "}")
for k in ("W_2", "W_3", "W_4", "W_5"):
    hops = [len(p) - 1 for p in by[k]["bellman_ford"]["paths"].values()]

# ── matrizes 5x5 ─────────────────────────────────────────────────────────────
V5 = (10, 20, 30, 40, 50)


def matrix_tabular(g):
    m = g["matrix"]["rows"]
    lines = ["\\begin{tabular}[t]{@{}r|rrrrr@{}}", "\\toprule",
             " & " + " & ".join(f"\\textbf{{{v}}}" for v in V5) + "\\\\ \\midrule"]
    for i, s in enumerate(V5):
        cells = [("0" if x == 0 else num(x, 2)) if x is not None else "$\\infty$" for x in m[i]]
        lines.append(f"\\textbf{{{s}}} & " + " & ".join(cells) + "\\\\")
    lines.append("\\bottomrule\n\\end{tabular}")
    return "\n".join(lines)


for g in graphs:
    if g["matrix"]["rows"]:
        out.append(f"\\expandafter\\def\\csname matriz@{g['name']}\\endcsname"
                   f"{{{matrix_tabular(g)}}}")
m2 = by["W_2"]["matrix"]["rows"]

def secs(mean, std=None, est=False):
    """Tempo em segundos: decimal de 3 algarismos significativos, ou 10^e se muito grande."""
    if mean is None:
        return DASH
    if mean >= 1e5:
        e = int(math.floor(math.log10(mean)))
        v = f"${num(mean / 10 ** e, 2).replace(',', '{,}')}\\cdot10^{{{e}}}$"
        return f"\\textit{{$\\approx$ {v}}}" if est else v
    v = sig(mean, 3)
    if est:
        return f"\\textit{{$\\approx$ {v}}}"
    places = len(v.split(",")[1]) if "," in v else 0
    return f"{v} $\\pm$ {num(std, places)}"


# ── tabela de tempos ─────────────────────────────────────────────────────────
DAG = "\\textsuperscript{$\\dagger$}"
rows = []
for g in graphs:
    n = g["name"]
    bf, fw, ap = g["bellman_ford"], g["floyd_warshall"], g["all_pairs_bf"]
    neg = bf["status"] == "ciclo_negativo"
    c_bf = secs(bf["mean_s"], bf["std_s"]) + (DAG if neg else "")
    t_fw, est = fw_time(g)
    c_fw = secs(fw["mean_s"], fw["std_s"]) + (DAG if neg else "")
    if est:
        c_fw = secs(t_fw, est=True)
    c_ap = secs(ap["mean_s"], ap["std_s"])
    if ap["estimated"]:
        c_ap = secs(ap["mean_s"], est=True)
    c_ap += DAG if neg else ""
    rows.append(" & ".join([tex(n), f"\\dado{{{n}.bf.rounds}}", c_bf, c_fw, c_ap]) + "\\\\")
out.append("\\newcommand{\\tabelaTempos}{" + "\n".join(rows) + "}")

# ── figura de tempos (pgfplots, escala log) ──────────────────────────────────
ok = [g for g in graphs if g["bellman_ford"]["status"] == "ok"]
series = {"bf": [], "fw": [], "fwe": [], "ap": [], "ape": []}
for i, g in enumerate(ok, 1):
    ap = g["all_pairs_bf"]
    t_fw, est = fw_time(g)
    series["bf"].append((i - 0.3, g["bellman_ford"]["mean_s"]))  # só na Tabela 2
    series["fwe" if est else "fw"].append((i + 0.28, t_fw))
    series["ape" if ap["estimated"] else "ap"].append((i - 0.28, ap["mean_s"]))


def coords(pts):
    def lab(y):
        scale, unit = unit_split(y)
        v = sig(y / scale, 2).replace("$-$", "")
        return v + "\\," + ("ano" if (unit == "anos" and v == "1,0") else unit)
    return " ".join(f"({y:.6g},{x:.2f}) [{lab(y)}]" for x, y in pts)


for k, pts in series.items():
    out.append(f"\\newcommand{{\\ser{k}}}{{{coords(pts)}}}")
out.append("\\newcommand{\\rotulosTempo}{" + ",".join(tex(g["name"]) for g in ok) + "}")

# ── contagens: ativos por rodada, arestas examinadas, memória ────────────────
for g in ok:
    n = g["name"]
    c = cby[n]
    pts = " ".join(f"({r['rodada']},{r['ativos'] / g['vertices']:.5f})" for r in c["rodadas"])
    out.append(f"\\expandafter\\def\\csname ativos@{n}\\endcsname{{{pts}}}")
    r = max(c["rodadas"], key=lambda r: r["ativos"])
    out.append(f"\\expandafter\\def\\csname pico@{n}\\endcsname{{{r['rodada']}}}")
    out.append(f"\\expandafter\\def\\csname picoy@{n}\\endcsname{{{r['ativos'] / g['vertices']:.5f}}}")


def lab10(x):
    return "$" + p10(x) + "$"


ops_fw = " ".join(f"({g['vertices'] ** 2:.6g},{i - 0.24:.2f}) [{lab10(g['vertices'] ** 2)}]"
                  for i, g in enumerate(ok, 1))
def ap_of(g):
    return cby[g["name"]]["todos_os_pares"]


ops_bf = " ".join(f"({ap_of(g)['arestas_examinadas_media']:.6g},{i + 0.24:.2f}) "
                  f"[{lab10(ap_of(g)['arestas_examinadas_media'])}]"
                  for i, g in enumerate(ok, 1))
ops_lab = "\n".join(
    f"\\node[font=\\footnotesize\\bfseries, anchor=east, text=gray!70!black] at (axis cs:1.5e17,{i}) "
    f"{{{sig(g['vertices'] ** 2 / ap_of(g)['arestas_examinadas_media'], 3)}$\\times$}};"
    for i, g in enumerate(ok, 1))
out.append(f"\\newcommand{{\\opsFW}}{{{ops_fw}}}\\newcommand{{\\opsBF}}{{{ops_bf}}}")
out.append("\\newcommand{\\opsRot}{" + ops_lab + "}")
mem = " ".join(f"({i},{g['floyd_warshall']['memory_needed_bytes'] / 2**30:.6g})"
               for i, g in enumerate(ok, 1))
out.append(f"\\newcommand{{\\memFW}}{{{mem}}}")
out.append(f"\\newcommand{{\\ramGiB}}{{{RAM_GIB}}}")

# ── W_1: ciclo negativo real ─────────────────────────────────────────────────
cyc = cby["W_1"]["ciclo_negativo"]
a, b = cyc["vertices"][0], cyc["vertices"][1]
w1, w2 = cyc["pesos"]
dado("cyc.a", str(a))
dado("cyc.b", str(b))
dado("cyc.sum", num(cyc["soma"], 2))
out.append(f"\\newcommand{{\\cicloA}}{{{a}}}\\newcommand{{\\cicloB}}{{{b}}}")
out.append(f"\\newcommand{{\\cicloSoma}}{{{cyc['soma']}}}")
dado("w1.rounds", num(cby["W_1"]["rodadas"][-1]["rodada"]))

# ── exemplo pequeno: grafo, CSR e rodadas do Bellman-Ford ────────────────────
V_ex, T, S = ex["vertices"], ex["destino"], ex["origem_dijkstra"]
edges = [tuple(e) for e in ex["arestas"]]
has = {(u, v) for u, v, _ in edges}
xs = [p[0] for p in ex["coordenadas"].values()]
ys = [p[1] for p in ex["coordenadas"].values()]


def pos(v, w, h):
    x, y = ex["coordenadas"][str(v)]
    fx = (x - min(xs)) / ((max(xs) - min(xs)) or 1)
    fy = (max(ys) - y) / ((max(ys) - min(ys)) or 1)
    return fx * w, fy * h


def wtxt(w):
    s = num(w, 2 if abs(w - round(w)) > 1e-9 else 0)
    return s.replace("$-$", "$-$")


def draw_graph(prefix, w, h, *, active=(), changed=(), dist=None, nxt=None, labels=True,
               order=None, hl_in=None, weights=True, vsize="vert", pw="peso"):
    L = []
    for v in range(1, V_ex + 1):
        x, y = pos(v, w, h)
        style = vsize
        if v in active:
            style += ",ativo"
        if v == T:
            style += ",destino"
        L.append(f"\\node[{style}] ({prefix}{v}) at ({x:.3f},{y:.3f}) {{{v}}};")
    nxt_edges = {(u, v) for u, v in (nxt or {}).items() if v is not None}
    for u, v, wt in edges:
        neg = wt < 0
        col = "ruim" if neg else "gray!65"
        extra = ""
        if hl_in is not None and v == hl_in:
            col, extra = ("ruim" if neg else "dest"), ",thick"
        bend = ",bend left=14" if (v, u) in has else ""
        if (u, v) in nxt_edges:
            L.append(f"\\draw[seta,{'ruim' if neg else 'bfc'},line width=1.35pt] ({prefix}{u}) to[{bend[1:] if bend else 'bend left=0'}] ({prefix}{v});")
        else:
            L.append(f"\\draw[seta,{col}{extra}] ({prefix}{u}) to[{bend[1:] if bend else 'bend left=0'}] ({prefix}{v});")
    if weights:
        for u, v, wt in edges:
            neg = wt < 0
            bend = ",bend left=14" if (v, u) in has else ""
            lbl_col = ",text=ruim,font=\\tiny\\bfseries" if neg else (",text=bfc,font=\\tiny\\bfseries" if (u, v) in nxt_edges else "")
            L.append(f"\\path ({prefix}{u}) to[{bend[1:] if bend else 'bend left=0'}] node[{pw}{lbl_col}] {{{wtxt(wt)}}} ({prefix}{v});")
    if dist is not None and labels:
        for v in range(1, V_ex + 1):
            d = dist[str(v)]
            if d is None:
                txt, st = "$\\infty$", "dinf"
            else:
                txt = wtxt(d)
                st = "dmud" if v in changed else "dfix"
            L.append(f"\\node[{st}, above=0.5pt of {prefix}{v}] {{{txt}}};")
    if order:
        for k, v in enumerate(order, 1):
            x, y = pos(v, w, h)
            angs = []
            for (u1, v1, _w) in edges:
                if u1 == v:
                    o = v1
                elif v1 == v:
                    o = u1
                else:
                    continue
                ox, oy = pos(o, w, h)
                angs.append(math.atan2(oy - y, ox - x))
            def _clear(a_):
                px, py = x + 0.5 * math.cos(math.radians(a_)), y + 0.5 * math.sin(math.radians(a_))
                m = 9.0
                for (u1, v1, _w) in edges:
                    (ax, ay), (bx, by_) = pos(u1, w, h), pos(v1, w, h)
                    t = ((px - ax) * (bx - ax) + (py - ay) * (by_ - ay)) / ((bx - ax) ** 2 + (by_ - ay) ** 2)
                    t = max(0.0, min(1.0, t))
                    m = min(m, math.hypot(px - (ax + t * (bx - ax)), py - (ay + t * (by_ - ay))))
                for o in range(1, V_ex + 1):
                    if o != v:
                        ox, oy = pos(o, w, h)
                        m = min(m, math.hypot(px - ox, py - oy) - 0.2)
                return m
            best = max(range(0, 360, 15), key=_clear)
            dx, dy = 0.5 * math.cos(math.radians(best)), 0.5 * math.sin(math.radians(best))
            L.append(f"\\node[ord] at ({x + dx:.3f},{y + dy:.3f}) {{{k}\\textsuperscript{{o}}}};")
    return "\n".join(L)


dado("ex.t", str(T))
# Figura 2: rodadas do Bellman-Ford (múltiplas pequenas).
rods = ex["bellman_ford"]["rodadas"]
npan = len(rods)
dado("ex.last", str(rods[-1]["rodada"]))
pans = []
wpan = 7.6
for r in rods:
    ch = set(r["mudaram"])
    body = draw_graph(f"r{r['rodada']}x", wpan * 0.94, wpan * 0.215, active=set(r["ativos"]),
                      changed=ch, dist=r["distancia"],
                      nxt={int(k): v for k, v in r["next"].items()}, weights=True,
                      vsize="vertp", pw="pesor")
    pans.append((r["rodada"], len(r["ativos"]), len(ch), body))
parts = []
for i, (k, na, nc, body) in enumerate(pans):
    parts.append("\\begin{minipage}[t]{%.3f\\linewidth}\\centering\n\\begin{tikzpicture}\n%s\n"
                 "\\end{tikzpicture}\\\\[0pt]{\\footnotesize \\textbf{rodada %d}\\,$\\cdot$\\,%d ativo%s}\n\\end{minipage}"
                 % (0.495, body, k, na, "s" if na != 1 else ""))
sep = []
for i, p in enumerate(parts):
    sep.append(p)
    if (i + 1) % 2 == 0 and i + 1 < len(parts):
        sep.append("\\\\[4pt]")
    elif i + 1 < len(parts):
        sep.append("\\hfill")
out.append("\\newcommand{\\figRodadas}{" + "\n".join(sep) + "}")

# ── conferência com a referência independente do W_2 ─────────────────────────
problems = []
for s, ref in REF_W2_BF.items():
    d = by["W_2"]["bellman_ford"]["distances"][s]
    if d is None or abs(d - ref) > 0.0051:
        problems.append(f"BF {s}->100: {d} vs {ref}")
for i in range(5):
    for j in range(5):
        if abs(m2[i][j] - REF_W2_MATRIX[i][j]) > 0.0051:
            problems.append(f"matriz [{V5[i]},{V5[j]}]: {m2[i][j]} vs {REF_W2_MATRIX[i][j]}")
for p in problems:
    print("DIVERGÊNCIA W_2:", p, file=sys.stderr)

# Chaves usadas no .tex e ainda sem valor.
used = set(re.findall(r"\\dado\{([^}]+)\}", (here / "relatorio.tex").read_text()))
used |= set(re.findall(r"\\dado\{([^}]+)\}", "\n".join(out)))
for key in sorted(k for k in used - set(dados) if "\\" not in k):
    print("aviso: chave sem valor:", key, file=sys.stderr)
    dado(key, DASH)

out.extend(f"\\expandafter\\def\\csname dado@{key}\\endcsname{{{value}}}"
           for key, value in dados.items())
(here / "tabelas.tex").write_text(
    "% Gerado por report/parte3/tabelas.py; não edite à mão.\n" + "\n".join(out) + "\n")
print(f"tabelas.tex: {len(dados)} valores, {len(graphs)} grafos, {len(problems)} divergências")
