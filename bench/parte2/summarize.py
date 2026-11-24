#!/usr/bin/env python3
"""Resume bench/results/parte2/* em presentation/parte2/data.js (window.TP2) e report/parte2/data.json.

Uso: python3 -I bench/summarize.py [--results DIR] [--data DIR] [--js ARQ] [--json ARQ]

Somente biblioteca padrão. Arquivos ausentes ou incompletos (benchmark ainda em
execução) não interrompem o script: o grafo é omitido ou o campo fica null, e o
motivo aparece em stderr.

Formatos lidos (ver bench/dijkstra_bench.cpp e part2/main.cpp):
  maquina.txt                chave=valor
  tempos_<grafo>.txt         [grafo] chave=valor, [execucoes] CSV, [resumo] chave=valor
  caminhos_W_<n>.txt         [grafo] chave=valor, [caminhos_minimos] chave=valor + CSV
  rede_colaboracao.txt       idem, com colunas de nomes
  DATA/rede_colaboracao.txt  opcional: pesos das arestas dos caminhos da rede (para o relatório)

  baixo_nivel.txt            [clock] [chase] [scan] [pops]... [ordem]... [layout]
                             (bench/lowlevel_bench.cpp; [pops] e [ordem] repetem por grafo)
  disputa.txt                [disputa]... vizinhos=, ghz=, CSV ns_por_estimativa (bench/run_contention.sh)
  contadores.txt             [contadores] CSV por execução (sudo bench/run_counters.sh, só macOS)

Tempo do vetor: cada extração varre V estimativas, então uma execução custa
~ c * V * R (R = vértices alcançados). c vem de execuções truncadas em cada grafo
([pops]); a validação compara c * V * R com as execuções completas do W_3 e do W_4.
"""

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPHS = ["W_3", "W_4", "W_5", "W_6", "W_7"]
VALIDATE_ON = ["W_3", "W_4"]
FRONTIERS = {"biblioteca": "library", "quatro_cadeias": "chains", "simd": "simd"}

# Medições do leitor no W_3 (experimento separado; não são geradas pelo benchmark).
READER = {
    "file": "W_3",
    "ifstream_ms": 1558,
    "from_chars_whole_ms": 211,
    "from_chars_block_ms": 381,
    "raw_read_ms": 40.5,
    "peak_before_reserve_mb": 332,
    "peak_after_reserve_mb": 251,
}


def log(message):
    print(f"summarize: {message}", file=sys.stderr)


def number(text):
    """int quando possível, depois float; senão a própria string."""
    text = text.strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        value = float(text)
        return value if math.isfinite(value) else None
    except ValueError:
        return text


def read_sections(path):
    """Divide o arquivo em {seção: [linhas]}; linhas antes da primeira seção ficam em ''."""
    sections = {"": []}
    current = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip("\r")
        match = re.fullmatch(r"\[(\w+)\]", line.strip())
        if match:
            current = match.group(1)
            sections.setdefault(current, [])
        elif line.strip():
            sections.setdefault(current, []).append(line)
    return sections


def read_blocks(path):
    """Como read_sections, mas preserva seções repetidas: [(seção, [linhas]), ...]."""
    blocks = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        match = re.fullmatch(r"\[(\w+)\]", line)
        if match:
            blocks.append((match.group(1), []))
        elif line and blocks:
            blocks[-1][1].append(line)
    return blocks


def csv_rows(lines):
    """Linhas CSV após o cabeçalho (primeira linha com vírgula); ignora linhas parciais."""
    rows, columns = [], None
    for line in lines:
        if "," not in line:
            continue
        fields = line.split(",")
        if columns is None:
            columns = fields
        elif len(fields) == len(columns):
            rows.append({k: number(v) for k, v in zip(columns, fields)})
    return rows


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def graph_name(path_text):
    match = re.search(r"(W_\d+)", path_text or "")
    return match.group(1) if match else path_text


def parse_lowlevel(path):
    if not path.exists():
        log(f"{path.name} ausente; lowlevel = null")
        return None
    result = {"clock_ghz": None, "chase": [], "scan": [], "pops": {}, "order": {}, "layout": []}
    for name, lines in read_blocks(path):
        if name == "clock":
            result["clock_ghz"] = number(key_values(lines).get("ghz", "nan"))
        elif name == "chase":
            result["chase"] = [[r["bytes"], r["ns_por_carga"]] for r in csv_rows(lines)]
        elif name == "scan":
            result["scan"] = [{"n": r["n"], "library": r["biblioteca_ns"],
                               "chains": r["quatro_cadeias_ns"], "simd": r["simd_ns"]}
                              for r in csv_rows(lines)]
        elif name == "pops":
            kv = key_values(lines)
            rows = csv_rows(lines)
            entry = {"vertices": number(kv["vertices"]), "edges": number(kv["arestas"]),
                     "limit": number(kv["limite"]), "checked": kv.get("conferencia_simd_heap") == "ok"}
            for label, key in FRONTIERS.items():
                mine = [r for r in rows if r["fronteira"] == label]
                entry[key] = {"runs": len(mine),
                              "ns": mean(r["ns_por_estimativa"] for r in mine),
                              "pops": mean(r["extracoes"] for r in mine)} if mine else None
            result["pops"][graph_name(kv.get("arquivo"))] = entry
        elif name == "ordem":
            kv = key_values(lines)
            rows = csv_rows(lines)
            labelings = {}
            for r in rows:
                labelings.setdefault(r["numeracao"], []).append(r)
            result["order"][graph_name(kv.get("arquivo"))] = {
                "vertices": number(kv["vertices"]), "edges": number(kv["arestas"]),
                "pushes": number(kv["pushes"]), "pops": number(kv["pops"]),
                "heap_peak": number(kv.get("pico_heap", "nan")),
                "labelings": {k: {"gap": v[0]["distancia_media_indices"], "runs": len(v),
                                  "mean_s": mean(r["s"] for r in v),
                                  "reached": mean(r["alcancados"] for r in v)}
                              for k, v in labelings.items()},
            }
        elif name == "layout":
            groups, peaks = {}, {}
            for r in csv_rows(lines):
                groups.setdefault((r["vertices"], r["numeracao"]), []).append(r)
            # Linhas "# N numeracao: pushes=… pops=… pico_heap=…" da execução contada.
            for line in lines:
                match = re.fullmatch(r"# (\d+) (\w+): .*pico_heap=(\d+)", line)
                if match:
                    peaks[(int(match.group(1)), match.group(2))] = int(match.group(3))
            result["layout"] = [{"vertices": v, "edges": rows[0]["arestas"], "labeling": label,
                                 "runs": len(rows), "ns_per_op": mean(r["ns_por_op"] for r in rows),
                                 "mean_s": mean(r["s"] for r in rows),
                                 "heap_peak": peaks.get((v, label))}
                                for (v, label), rows in groups.items()]
    return result


def median(values):
    values = sorted(values)
    n = len(values)
    return (values[(n - 1) // 2] + values[n // 2]) / 2 if values else None


def parse_contention(path):
    """{vizinhos: {"pops_ns": [...], "scan": {n: [ns da biblioteca por rodada]}}}."""
    if not path.exists():
        log(f"{path.name} ausente; contention = null")
        return None
    result = {}
    for name, lines in read_blocks(path):
        if name != "disputa":
            continue
        kind = key_values(lines).get("vizinhos")
        split = next((i for i, line in enumerate(lines) if line.startswith("n,")), len(lines))
        entry = result.setdefault(kind, {"pops_ns": [], "scan": {}})
        entry["pops_ns"] += [r["ns_por_estimativa"] for r in csv_rows(lines[:split])]
        for r in csv_rows(lines[split:]):
            entry["scan"].setdefault(r["n"], []).append(r["biblioteca_ns"])
    for entry in result.values():
        entry["pops_median_ns"] = median(entry["pops_ns"])
        entry["scan_median_ns"] = {n: median(v) for n, v in entry["scan"].items()}
    return result


def parse_counters(path):
    """{"grafo/numeracao/fronteira": {coluna: média das rodadas}} de contadores.txt."""
    if not path.exists():
        log(f"{path.name} ausente; counters = null")
        return None
    groups = {}
    for name, lines in read_blocks(path):
        if name != "contadores":
            continue
        for r in csv_rows(lines):
            key = f"{graph_name(r['grafo'])}/{r['numeracao']}/{r['fronteira']}"
            groups.setdefault(key, []).append(r)
    result = {}
    for key, rows in groups.items():
        entry = {c: mean(r[c] for r in rows) for c in rows[0] if isinstance(rows[0][c], (int, float))}
        entry["runs"] = len(rows)
        result[key] = entry
    return result


def key_values(lines):
    result = {}
    for line in lines:
        if "=" in line and "," not in line.split("=", 1)[0]:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def stats(values):
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return None
    n = len(values)
    mean = sum(values) / n
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
    return {"runs": n, "mean_s": mean, "std_s": std, "min_s": min(values), "max_s": max(values)}


def parse_machine(path):
    if not path.exists():
        log(f"{path.name} ausente; machine = null")
        return None
    kv = key_values(read_sections(path)[""])
    return {
        "cpu": kv.get("cpu"),
        "memory_bytes": number(kv["memoria_bytes"]) if "memoria_bytes" in kv else None,
        "compiler": kv.get("compilador"),
        "seed": number(kv["semente"]) if "semente" in kv else None,
        "k": number(kv["k"]) if "k" in kv else None,
        "date": kv.get("data"),
    }


def parse_times(path):
    """Lê tempos_*.txt; tolera arquivo truncado (benchmark em andamento)."""
    sections = read_sections(path)
    header = key_values(sections.get("grafo", []))
    if "vertices" not in header:
        return None

    runs = []
    columns = None
    for line in sections.get("execucoes", []):
        fields = line.split(",")
        if columns is None:
            columns = fields
            continue
        if len(fields) != len(columns):
            continue  # linha parcial no fim de um arquivo ainda sendo escrito
        row = dict(zip(columns, fields))
        try:
            runs.append({
                "source": int(row["origem"]),
                "reached": int(row["alcancados"]),
                "heap_s": float(row["heap_s"]),
                "vector_s": float(row["vetor_s"]) if row["vetor_s"] else None,
            })
        except (KeyError, ValueError):
            continue

    summary = key_values(sections.get("resumo", []))
    return {"header": header, "runs": runs, "summary": summary}


PLAIN_ROW = re.compile(r"^(\d+),([-+0-9.eE]+),(\d+(?: \d+)*)$")
NAMED_ROW = re.compile(r"^(\d+),(.*?),([-+0-9.eE]+),(\d+(?: \d+)*),(.*)$")


def parse_paths(path, named):
    """Linhas de [caminhos_minimos]; com nomes, o nome do destino pode conter vírgulas."""
    sections = read_sections(path)
    graph = key_values(sections.get("grafo", []))
    lines = sections.get("caminhos_minimos", [])
    meta = key_values([line for line in lines if "=" in line and not line[0].isdigit()])
    rows = [line for line in lines if line[:1].isdigit()]

    paths = []
    for line in rows:
        status = None
        for marker in ("inalcancavel", "fora_do_grafo"):
            if line.endswith("," + marker):
                status = marker
                head = line[: -len(marker) - 1]
        if status:
            target, _, name = head.partition(",")
            entry = {"target": int(target), "distance": None, "path": None, "status": status}
            if named:
                entry.update(name=name, path_names=None)
            paths.append(entry)
            continue

        match = (NAMED_ROW if named else PLAIN_ROW).match(line)
        if not match:
            log(f"{path.name}: linha não reconhecida: {line[:80]}")
            continue
        vertices = [int(v) for v in match.group(4 if named else 3).split()]
        entry = {
            "target": int(match.group(1)),
            "distance": float(match.group(3 if named else 2)),
            "path": vertices,
            "status": "ok",
        }
        if named:
            names = match.group(5).split(" -> ")
            entry["name"] = match.group(2)
            entry["path_names"] = names if len(names) == len(vertices) else None
        paths.append(entry)

    return {"graph": graph, "meta": meta, "paths": paths}


def matrix_bytes(vertices):
    # Matriz de bytes V x V mais matriz de pesos double V x V (docs/PROJETO.md: 9V²).
    return vertices * vertices * (1 + 8)


def summarize_graph(name, times, paths):
    header = times["header"]
    runs = times["runs"]
    summary = times["summary"]
    vertices = number(header["vertices"])
    heap = stats([r["heap_s"] for r in runs])
    vector_runs = [r for r in runs if r["vector_s"] is not None]
    vector = stats([r["vector_s"] for r in vector_runs])
    if vector:
        vector = {k: vector[k] for k in ("runs", "mean_s", "std_s")}
    peak = summary.get("pico_rss_bytes") or header.get("pico_rss_apos_leitura_bytes")
    expected_runs = number(header.get("k", "0")) or 0

    complete = bool(summary) and len(runs) == expected_runs
    if not complete:
        log(f"{name}: {len(runs)}/{expected_runs} execuções, resumo "
            f"{'presente' if summary else 'ausente'} (incompleto)")
    if summary.get("divergencias", "0") != "0":
        log(f"{name}: divergencias={summary['divergencias']} entre heap e vetor")

    return {
        "name": name,
        "vertices": vertices,
        "edges": number(header["arestas"]),
        "load_s": number(header["leitura_s"]) if "leitura_s" in header else None,
        "memory_bytes": number(header["memoria_bytes"]) if "memoria_bytes" in header else None,
        "peak_rss_bytes": number(peak) if peak else None,
        "matrix_bytes_estimate": matrix_bytes(vertices),
        "heap": heap,
        "vector": vector,
        "vector_estimate_s": None,  # preenchido por vector_cost
        "vector_variants_s": None,
        "reached_mean": (sum(r["reached"] for r in runs) / len(runs)) if runs else None,
        "paths": paths["paths"] if paths else None,
        "complete": complete,
        "mismatches": number(summary["divergencias"]) if "divergencias" in summary else None,
        "heap_runs": [r["heap_s"] for r in runs],
        "vector_runs": [r["vector_s"] for r in vector_runs],
        "_runs": runs,
    }


def path_weights(graph_file, paths):
    """Peso de cada aresta dos caminhos: menor peso entre arestas repetidas do arquivo."""
    wanted = {}
    for path in paths:
        for u, v in zip(path, path[1:]):
            wanted[(min(u, v), max(u, v))] = math.inf
    with open(graph_file, encoding="utf-8") as lines:
        next(lines)
        for line in lines:
            fields = line.split()
            if len(fields) != 3:
                continue
            u, v = int(fields[0]), int(fields[1])
            key = (min(u, v), max(u, v))
            if key in wanted:
                wanted[key] = min(wanted[key], float(fields[2]))
    return [[wanted[(min(u, v), max(u, v))] for u, v in zip(path, path[1:])] for path in paths]


def vector_cost(graphs, lowlevel):
    """c por grafo, medido nas execuções truncadas; validação contra execuções completas."""
    pops = (lowlevel or {}).get("pops", {})
    if not pops:
        log("baixo_nivel.txt sem [pops]; sem tempo do vetor")
        return None
    for graph in graphs:
        entry = pops.get(graph["name"])
        if not entry or not entry["library"] or graph["reached_mean"] is None:
            log(f"{graph['name']}: sem [pops]; vector_estimate_s = null")
            continue
        scale = graph["vertices"] * graph["reached_mean"] * 1e-9
        graph["vector_estimate_s"] = entry["library"]["ns"] * scale
        graph["vector_variants_s"] = {key: entry[key]["ns"] * scale
                                      for key in FRONTIERS.values() if entry[key]}

    validation = []
    for graph in graphs:
        entry = pops.get(graph["name"])
        measured = [r for r in graph["_runs"] if r["vector_s"] is not None]
        if graph["name"] not in VALIDATE_ON or not entry or not measured:
            continue
        # Custo por estimativa de cada execução completa; a mediana resiste às poucas execuções
        # atrasadas por outros processos (a média fica em measured_mean_ns).
        per_run = sorted(r["vector_s"] / (graph["vertices"] * r["reached"]) * 1e9 for r in measured)
        middle = len(per_run) // 2
        median_ns = per_run[middle] if len(per_run) % 2 else (per_run[middle - 1] + per_run[middle]) / 2
        predicted_ns = entry["library"]["ns"]
        validation.append({
            "graph": graph["name"],
            "runs": len(measured),
            "measured_ns": median_ns,
            "measured_mean_ns": mean(per_run),
            "fastest_ns": per_run[0],
            "slowest_ns": per_run[-1],
            "predicted_ns": predicted_ns,
            "error_pct": (predicted_ns - median_ns) / median_ns * 100,
        })
    return {"ns_per_estimate": {name: e["library"]["ns"] for name, e in pops.items() if e["library"]},
            "validation": validation}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=ROOT / "bench" / "results" / "parte2")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--js", type=Path, default=ROOT / "presentation" / "parte2" / "data.js")
    parser.add_argument("--json", type=Path, default=ROOT / "report" / "parte2" / "data.json")
    args = parser.parse_args()
    results = args.results

    graphs = []
    for name in GRAPHS:
        times_path = results / f"tempos_{name}.txt"
        paths_path = results / f"caminhos_{name}.txt"
        times = parse_times(times_path) if times_path.exists() else None
        if not times:
            log(f"{times_path.name} ausente ou sem [grafo]; {name} omitido")
            continue
        paths = parse_paths(paths_path, named=False) if paths_path.exists() else None
        if not paths:
            log(f"{paths_path.name} ausente; paths = null")
        graphs.append(summarize_graph(name, times, paths))

    lowlevel = parse_lowlevel(results / "baixo_nivel.txt")
    fit = vector_cost(graphs, lowlevel)

    colab = None
    colab_paths_file = results / "rede_colaboracao.txt"
    colab_times_file = results / "tempos_rede_colaboracao.txt"
    colab_paths = parse_paths(colab_paths_file, named=True) if colab_paths_file.exists() else None
    colab_times = parse_times(colab_times_file) if colab_times_file.exists() else None
    if not colab_paths:
        log(f"{colab_paths_file.name} ausente")
    if not colab_times:
        log(f"{colab_times_file.name} ausente; colab.heap = null")
    if colab_paths or colab_times:
        header = (colab_paths or {}).get("graph") or (colab_times or {}).get("header") or {}
        runs = colab_times["runs"] if colab_times else []
        reached = sum(r["reached"] for r in runs) / len(runs) if runs else None
        vertices = number(header["vertices"]) if "vertices" in header else None
        colab = {
            "vertices": vertices,
            "edges": number(header["arestas"]) if "arestas" in header else None,
            "memory_bytes": number(header["memoria_bytes"]) if "memoria_bytes" in header else None,
            "source_name": colab_paths["meta"].get("origem_nome") if colab_paths else None,
            "source": number(colab_paths["meta"]["origem"])
            if colab_paths and "origem" in colab_paths["meta"] else None,
            "paths": [
                {"target": p["target"], "name": p.get("name"), "distance": p["distance"],
                 "path": p["path"], "path_names": p.get("path_names"), "status": p["status"]}
                for p in colab_paths["paths"]
            ] if colab_paths else None,
            "heap": stats([r["heap_s"] for r in runs]),
            "runs": [[r["reached"], r["heap_s"]] for r in runs],
            "reached_mean": reached,
            "load_s": number(colab_times["header"]["leitura_s"])
            if colab_times and "leitura_s" in colab_times["header"] else None,
            # Sem [pops] na rede: usa o c do W_3, que cabe no mesmo nível de cache.
            "vector_estimate_s": fit["ns_per_estimate"]["W_3"] * 1e-9 * vertices * reached
            if fit and "W_3" in fit["ns_per_estimate"] and vertices and reached else None,
        }

    colab_graph_file = args.data / "rede_colaboracao.txt"
    if colab and colab["paths"] and colab_graph_file.exists():
        found = [p for p in colab["paths"] if p["path"]]
        for p, weights in zip(found, path_weights(colab_graph_file, [p["path"] for p in found])):
            p["edge_weights"] = weights
    elif colab:
        log(f"{colab_graph_file} ausente; pesos das arestas dos caminhos omitidos")

    for graph in graphs:
        del graph["_runs"]

    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "machine": parse_machine(results / "maquina.txt"),
        "graphs": graphs,
        "fit": fit,
        "lowlevel": lowlevel,
        "contention": parse_contention(results / "disputa.txt"),
        "counters": parse_counters(results / "contadores.txt"),
        "colab": colab,
        "reader": READER,
    }

    text = json.dumps(data, ensure_ascii=False, indent=1)
    args.js.parent.mkdir(parents=True, exist_ok=True)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.js.write_text(
        "// Gerado por bench/summarize.py a partir de bench/results/parte2/. Não editar.\n"
        f"window.TP2 = {text};\n", encoding="utf-8")
    args.json.write_text(text + "\n", encoding="utf-8")
    log(f"{len(graphs)} grafo(s); escrito {args.js} e {args.json}")


if __name__ == "__main__":
    main()
