#!/bin/sh
# Estudos de caso da Parte 2: relatórios de caminhos mínimos e tempos de Dijkstra.
# Uso: bench/run_case_studies.sh [DIRETORIO_DOS_DADOS]
# Os tempos só valem com a máquina ociosa; os grafos são lidos de data/ por padrão.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
data=${1:-"$root/data"}
results="$root/bench/results/parte2"
seed=2026
k=100

mkdir -p "$results"
cmake --preset csr >/dev/null
cmake --build --preset csr >/dev/null

{
    echo "data=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "cpu=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || uname -m)"
    echo "memoria_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo desconhecida)"
    echo "compilador=$(c++ --version | head -n 1)"
    echo "semente=$seed"
    echo "k=$k"
} >"$results/maquina.txt"

part2="$root/build/csr/cos_part2"
bench="$root/build/csr/cos_bench2"

"$part2" "$data/rede_colaboracao.txt" "$results/rede_colaboracao.txt" \
    "$data/rede_colaboracao_vertices.txt"

# O vetor custa O(V·R) por origem: 100 execuções no W_3, cinco no W_4 e nenhuma nos maiores.
for entry in 3:100 4:5 5:0 6:0 7:0; do
    graph=${entry%%:*}
    vector_runs=${entry##*:}
    "$part2" "$data/grafo_W_$graph.txt" "$results/caminhos_W_$graph.txt"
    "$bench" "$data/grafo_W_$graph.txt" "$k" "$seed" "$vector_runs" >"$results/tempos_W_$graph.txt"
done

"$bench" "$data/rede_colaboracao.txt" "$k" "$seed" 0 >"$results/tempos_rede_colaboracao.txt"
