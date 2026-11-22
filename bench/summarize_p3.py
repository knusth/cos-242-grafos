#!/usr/bin/env python3
"""Resume bench/results/parte3/* em report/parte3/data.json (relatório e apresentação da Parte 3).

Uso: python3 -I bench/summarize_p3.py [DIR_RESULTADOS] [SAIDA.json]
     padrões: bench/results/parte3 e report/parte3/data.json

Entradas (formatos de bench/caminhos_bench.cpp e part3/main.cpp):
  maquina.txt            cpu, memória, threads, compilador, data
  p3_W_n.txt             cos_bench3: [grafo], [bellman_ford], [floyd_warshall],
                         [bellman_ford_todos_pares]
  p3_W_n.relatorio.txt   cos_part3: distâncias e caminhos (sem tempo)
Funciona com resultados parciais: o que falta vira null e "status": "pendente".

Esquema de data.json:
  generated_at, source_dir
  machine: {cpu, memory_bytes, threads, compiler, date}
  graphs: lista, em ordem W_1..W_5, de
    name ("W_1"), file ("p3_W_1.txt"), complete (bool: bench e relatório presentes)
    vertices, edges, negative_weights (bool), mean_degree, load_s, graph_memory_bytes
    bellman_ford: {
      status          "ok" | "ciclo_negativo" | "pendente"
      target          100 (rótulo do arquivo, base 1)
      runs, mean_s, std_s, min_s     média de 10 execuções, uma thread, sem leitura
      rounds, negative_cycle         rodadas executadas; houve detecção
      neg_cycle_reaches_target, neg_cycle_in_graph   (bool, do relatório)
      distances       {"10": d|null, "20": ..., "30": ...} até o vértice 100;
                      null se inalcançável ou se há ciclo negativo (d = -inf)
      paths           {"10": [vértices...], ...}
    }
    floyd_warshall: {
      status          "ok" | "memoria_insuficiente" | "ciclo_negativo" | "pendente"
      memory_needed_bytes (12*V^2), memory_needed_gib, limit_gib
      threads, runs, mean_s, std_s, min_s, negative_cycle
    }
    matrix: {source: "floyd_warshall" | "bellman_ford" | null, vertices: [10,...,50],
             rows: [[d|null]*5]*5}   linha = origem, coluna = destino; null = inf/ausente
    all_pairs_bf: {
      status          "ok" | "ciclo_negativo" | "pendente"
      threads, runs, mean_s, std_s
      estimated       true: K destinos medidos numa thread e extrapolados por V
      sample          K (destinos medidos), vertices
      negative_cycle
    }
    ops: {fw_relaxations (V^3), bf_ops_upper_bound (V * rounds * E)}
  peak_rss_bytes por grafo em "peak_rss_bytes".
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "bench/results/parte3"
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "report/parte3/data.json"

NAMES = [1, 2, 3, 4, 5]
SOURCES = (10, 20, 30)
FW_VERTICES = (10, 20, 30, 40, 50)


def number(text):
    try:
        return float(text)
    except ValueError:
        return None


def parse(path):
    """{secao: {"kv": {chave: texto}, "tables": [(cabeçalho, [linhas])]}}."""
    out = {}
    if not path.exists():
        return out
    section = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.fullmatch(r"\[(\w+)\]", line)
        if m:
            section = out.setdefault(m.group(1), {"kv": {}, "tables": []})
        elif section is None:
            continue
        elif re.match(r"^\w+=", line):
            key, _, value = line.partition("=")
            section["kv"][key] = value
        elif "," in line:
            if line.startswith(("origem,", "origem\\", "execucao,")) or not section["tables"]:
                section["tables"].append((line.split(","), []))
            else:
                section["tables"][-1][1].append(line.split(","))
    return out


def stats(kv):
    return {"mean_s": number(kv.get("media_s", "")), "std_s": number(kv.get("desvio_s", "")),
            "min_s": number(kv.get("min_s", ""))}


def yes(text):
    return None if text is None else text == "sim"


def table(section, first_header, second=None):
    for header, rows in section["tables"]:
        if header[0].startswith(first_header) and (second is None or header[1] == second):
            return header, rows
    return None, []


def matrix_from(section):
    header, rows = table(section, "origem\\")
    if header is None:
        return None
    dest = [int(x) for x in header[1:]]
    by_row = {int(r[0]): [number(c) for c in r[1:]] for r in rows}
    return [[by_row.get(s, [None] * 5)[dest.index(t)] if t in dest else None
             for t in FW_VERTICES] for s in FW_VERTICES]


machine_kv = {}
mpath = src / "maquina.txt"
if mpath.exists():
    for line in mpath.read_text().splitlines():
        k, _, v = line.partition("=")
        machine_kv[k] = v
machine = {
    "cpu": machine_kv.get("cpu"),
    "memory_bytes": int(machine_kv["memoria_bytes"]) if "memoria_bytes" in machine_kv else None,
    "threads": int(machine_kv["threads"]) if "threads" in machine_kv else None,
    "compiler": machine_kv.get("compilador"),
    "date": machine_kv.get("data"),
}

graphs = []
for n in NAMES:
    name = f"p3_W_{n}"
    bench = parse(src / f"{name}.txt")
    rel = parse(src / f"{name}.relatorio.txt")
    g = {"name": f"W_{n}", "file": f"{name}.txt", "complete": bool(bench) and bool(rel)}
    gk = {**rel.get("grafo", {"kv": {}})["kv"], **bench.get("grafo", {"kv": {}})["kv"]}
    V = int(gk["vertices"]) if "vertices" in gk else None
    E = int(gk["arestas"]) if "arestas" in gk else None
    g["vertices"], g["edges"] = V, E
    g["negative_weights"] = yes(gk.get("pesos_negativos"))
    g["mean_degree"] = number(gk.get("grau_medio", ""))
    g["load_s"] = number(gk.get("leitura_s", ""))
    g["graph_memory_bytes"] = int(gk["memoria_bytes"]) if "memoria_bytes" in gk else None
    g["peak_rss_bytes"] = (int(bench["resumo"]["kv"]["pico_rss_bytes"])
                           if "resumo" in bench else None)

    # ── Bellman-Ford até o vértice 100 ──
    bf = {"status": "pendente", "target": 100, "runs": None, "mean_s": None, "std_s": None,
          "min_s": None, "rounds": None, "negative_cycle": None,
          "neg_cycle_reaches_target": None, "neg_cycle_in_graph": None,
          "distances": {str(s): None for s in SOURCES}, "paths": {}}
    if "bellman_ford" in bench:
        sec = bench["bellman_ford"]
        _, rows = table(sec, "execucao")
        bf.update(stats(sec["kv"]))
        bf["runs"] = len(rows)
        if rows:
            bf["rounds"] = int(rows[0][2])
            bf["negative_cycle"] = rows[0][3] == "sim"
            bf["status"] = "ciclo_negativo" if bf["negative_cycle"] else "ok"
        if bf["mean_s"] is None:
            bf["status"] = "pendente"
    if "bellman_ford" in rel:
        sec = rel["bellman_ford"]
        bf["neg_cycle_reaches_target"] = yes(sec["kv"].get("ciclo_negativo_alcanca_destino"))
        bf["neg_cycle_in_graph"] = yes(sec["kv"].get("ciclo_negativo_no_grafo"))
        bf["rounds"] = int(sec["kv"]["rodadas"]) if "rodadas" in sec["kv"] else bf["rounds"]
        if sec["kv"].get("situacao") == "ciclo_negativo":
            bf["status"] = "ciclo_negativo"
        _, rows = table(sec, "origem", "distancia")
        for r in rows:
            bf["distances"][r[0]] = number(r[1])
            if len(r) > 2 and r[2]:
                bf["paths"][r[0]] = [int(x) for x in r[2].split()]
    g["bellman_ford"] = bf

    # ── Floyd-Warshall ──
    needed = 12 * V * V if V else None
    fw = {"status": "pendente", "memory_needed_bytes": needed,
          "memory_needed_gib": needed / 2**30 if needed else None, "limit_gib": None,
          "threads": None, "runs": None, "mean_s": None, "std_s": None, "min_s": None,
          "negative_cycle": None}
    if "floyd_warshall" in bench:
        sec = bench["floyd_warshall"]
        kv = sec["kv"]
        fw["limit_gib"] = number(kv.get("limite_gib", ""))
        if kv.get("situacao") == "memoria_insuficiente":
            fw["status"] = "memoria_insuficiente"
        else:
            _, rows = table(sec, "execucao")
            fw.update(stats(kv))
            fw["threads"] = int(kv["threads"]) if "threads" in kv else None
            fw["runs"] = len(rows)
            if rows:
                fw["negative_cycle"] = rows[0][2] == "sim"
                fw["status"] = "ciclo_negativo" if fw["negative_cycle"] else "ok"
    elif "floyd_warshall" in rel:
        st = rel["floyd_warshall"]["kv"].get("situacao")
        if st in ("memoria_insuficiente", "ciclo_negativo"):
            fw["status"] = st
    g["floyd_warshall"] = fw

    # ── matriz 5x5 ──
    mat = {"source": None, "vertices": list(FW_VERTICES), "rows": None}
    if "floyd_warshall" in rel and (m := matrix_from(rel["floyd_warshall"])):
        mat["source"], mat["rows"] = "floyd_warshall", m
    elif "distancias_por_bellman_ford" in rel and (
            m := matrix_from(rel["distancias_por_bellman_ford"])):
        mat["source"], mat["rows"] = "bellman_ford", m
    g["matrix"] = mat

    # ── todos os pares por Bellman-Ford ──
    ap = {"status": "pendente", "threads": None, "runs": None, "mean_s": None, "std_s": None,
          "estimated": None, "sample": None, "vertices": V, "negative_cycle": None}
    if "bellman_ford_todos_pares" in bench:
        sec = bench["bellman_ford_todos_pares"]
        kv = sec["kv"]
        _, rows = table(sec, "execucao")
        ap.update({"mean_s": number(kv.get("media_s", "")), "std_s": number(kv.get("desvio_s", "")),
                   "threads": int(kv["threads"]) if "threads" in kv else None,
                   "estimated": yes(kv.get("estimado")),
                   "sample": int(kv["destinos_medidos"]) if "destinos_medidos" in kv else None,
                   "runs": len(rows)})
        if rows:
            ap["negative_cycle"] = any(int(r[3]) > 0 for r in rows)
            ap["status"] = "ciclo_negativo" if ap["negative_cycle"] else "ok"
        if ap["mean_s"] is None:  # execução em andamento: só algumas rodadas impressas
            ap["status"] = "pendente"
    g["all_pairs_bf"] = ap

    g["ops"] = {
        "fw_relaxations": V ** 3 if V else None,
        "bf_ops_upper_bound": (V * bf["rounds"] * E if V and E and bf["rounds"] else None),
    }
    graphs.append(g)

out = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "source_dir": str(src.relative_to(root)) if src.is_relative_to(root) else str(src),
       "machine": machine, "graphs": graphs}
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
done = sum(1 for g in graphs if g["complete"])
print(f"{dst}: {done}/{len(graphs)} grafos completos")
