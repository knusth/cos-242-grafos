#!/bin/sh
# Experimentos de baixo nível (bench/lowlevel_bench.cpp); cerca de 10 min com a máquina ociosa.
# Uso: bench/run_lowlevel.sh [DIRETORIO_DOS_DADOS]
set -eu

root=$(cd "$(dirname "$0")/../.." && pwd)
data=${1:-"$root/data"}
out="$root/bench/results/parte2/baixo_nivel.txt"
seed=2026

cmake --preset csr -DCOS_BUILD_BENCHMARKS=ON >/dev/null
cmake --build --preset csr >/dev/null
low="$root/build/csr/bench/cos_lowlevel"

{
    "$low" clock
    "$low" chase
    "$low" scan
    # Primeiras extrações do vetor: cerca de 10 s por origem e fronteira no W_5 a W_7.
    for entry in 3:100000 4:10000 5:1500 6:1500 7:300; do
        "$low" pops "$data/grafo_W_${entry%%:*}.txt" 5 "${entry##*:}" "$seed"
    done
    for graph in 3 5; do
        "$low" order "$data/grafo_W_$graph.txt" 5 "$seed"
    done
    "$low" layout cabecalho 0 0
    for vertices in 100000 1000000 10000000 50000000; do
        "$low" layout "$vertices" 8 3
    done
} >"$out"
