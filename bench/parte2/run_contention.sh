#!/bin/sh
# Por que as execuções do vetor variam. Em cada rodada, três condições: sozinho, com quatro
# vizinhos que só usam registradores e com quatro que releem 64 MB. Alternar as condições
# espalha a carga de fundo da máquina igualmente entre elas. Mede o [pops] do W_4 e o [scan]:
# no scan com n pequeno o vetor está no L1, que é de cada núcleo; vizinhos não o expulsam de lá.
# Cerca de 40 min.
# Uso: bench/run_contention.sh [DIRETORIO_DOS_DADOS]
set -eu

root=$(cd "$(dirname "$0")/../.." && pwd)
data=${1:-"$root/data"}
out="$root/bench/results/parte2/disputa.txt"
seed=7
rounds=6

cmake --preset csr -DCOS_BUILD_BENCHMARKS=ON >/dev/null
cmake --build --preset csr >/dev/null
low="$root/build/csr/bench/cos_lowlevel"
busy="$root/build/csr/bench/cos_busy"

neighbors=""
stop() { [ -n "$neighbors" ] && kill $neighbors 2>/dev/null; neighbors=""; }
trap stop EXIT INT TERM

{
    round=1
    while [ $round -le $rounds ]; do
        for kind in nenhum registradores memoria; do
            if [ "$kind" != nenhum ]; then
                for _ in 1 2 3 4; do
                    "$busy" "$kind" &
                    neighbors="$neighbors $!"
                done
                sleep 1
            fi
            echo "[disputa]"
            echo "rodada=$round"
            echo "vizinhos=$kind"
            "$low" pops "$data/grafo_W_4.txt" 2 20000 $seed | grep -E '^(fronteira|biblioteca),'
            "$low" scan | grep -v '^\['
            stop
            sleep 3
        done
        round=$((round + 1))
    done
} >"$out"
