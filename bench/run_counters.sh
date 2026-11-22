#!/bin/sh
# Contadores de hardware (faltas no L1 e na TLB, ciclos esperando a memória) durante Dijkstra.
# Precisa de root para ler os contadores; compile antes sem sudo:
#   cmake --build --preset csr && sudo bench/run_counters.sh
# Cerca de 5 min.
# Uso: sudo bench/run_counters.sh [DIRETORIO_DOS_DADOS]
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
data=${1:-"$root/data"}
out="$root/bench/results/parte2/contadores.txt"
seed=2026
counters="$root/build/csr/cos_counters"

[ -x "$counters" ] || { echo "compile antes: cmake --build --preset csr" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo "rode com sudo" >&2; exit 1; }

{
    "$counters" counters cabecalho
    # Heap completo e as primeiras extrações do vetor nas mesmas origens.
    for entry in 3:2000 4:500 5:100; do
        "$counters" counters "$data/grafo_W_${entry%%:*}.txt" 3 "${entry##*:}" "$seed"
    done
    for vertices in 100000 1000000 10000000; do
        "$counters" counters local "$vertices" 8 3
    done
} >"$out"
# O arquivo fica com o dono de quem chamou o sudo.
[ -n "${SUDO_USER:-}" ] && chown "$SUDO_USER" "$out"
echo "ok: $out"
