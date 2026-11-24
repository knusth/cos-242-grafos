#!/bin/sh
# Estudo de caso da Parte 3 (grafos oficiais p3_W_1 ... p3_W_5).
# Uso: bench/run_part3.sh [DIRETORIO_DOS_DADOS] [DIRETORIO_DE_RESULTADOS]
#      padrões: data/ e bench/results/parte3/
# Variáveis: FW_RODADAS (padrão 10), FW_LIMITE_GIB (padrão 16), GRAFOS (padrão: todos, nesta ordem) para medir de novo só alguns grafos.
#
# Protocolo (máquina: Apple M3 Pro, 11 núcleos; todas as threads, via hw.ncpu ou nproc):
#   - Compila uma vez em build/csr (Release, -DCOS_MATRIX=OFF): cos_bench3 e cos_part3.
#   - Por grafo, uma chamada de cos_bench3 com 10 rodadas e --threads = núcleos:
#       * Bellman-Ford até o vértice 100: 10 rodadas;
#       * todos-pares por Bellman-Ford: 10 rodadas; completo para W_1 e W_2 e amostra de
#         destinos (extrapolada por V) para W_3 (200), W_4 (30) e W_5 (10);
#       * Floyd-Warshall: --fw com FW_RODADAS rodadas (o binário pula com
#         situacao=memoria_insuficiente quando a matriz passa de FW_LIMITE_GIB, ou seja, W_3+).
#   - Por grafo, cos_part3 grava NOME.relatorio.txt (tabelas com caminhos; sem medição de tempo).
#   - Ordem: W_1, W_3, W_4, W_5 e W_2 por último (seu Floyd-Warshall leva ~12 min por rodada),
#     para que resultados parciais já sirvam.
#   - Saídas: RESULTADOS/maquina.txt, RESULTADOS/NOME.txt e RESULTADOS/NOME.relatorio.txt.
# Tempo total esperado: ~3 h, dominado por 10 x Floyd-Warshall em W_2.
# Os tempos só valem com a máquina ociosa.
set -eu

root=$(cd "$(dirname "$0")/../.." && pwd)
data=${1:-"$root/data"}
results=${2:-"$root/bench/results/parte3"}
fw_runs=${FW_RODADAS:-10}
fw_limit=${FW_LIMITE_GIB:-16}
grafos=${GRAFOS:-"p3_W_1 p3_W_3 p3_W_4 p3_W_5 p3_W_2"}
runs=10
ncpu=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 1)

# Destinos medidos no todos-pares por Bellman-Ford (0 = completo).
amostra_de() {
    case $1 in
        p3_W_1 | p3_W_2) echo 0 ;;
        p3_W_3) echo 200 ;;
        p3_W_4) echo 30 ;;
        p3_W_5) echo 10 ;;
        *) echo "grafo desconhecido: $1" >&2; exit 1 ;;
    esac
}

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2; }

mkdir -p "$results"
log "compilando build/csr"
cmake -S "$root" -B "$root/build/csr" -DCMAKE_BUILD_TYPE=Release -DCOS_MATRIX=OFF -DCOS_BUILD_BENCHMARKS=ON >/dev/null
cmake --build "$root/build/csr" --target cos_bench3 cos_part3 >/dev/null
bench="$root/build/csr/bench/cos_bench3"
part3="$root/build/csr/cos_part3"

{
    echo "data=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "cpu=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo desconhecida)"
    echo "memoria_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
    echo "threads=$ncpu"
    echo "compilador=$(c++ --version | head -n 1)"
} >"$results/maquina.txt"

for name in $grafos; do
    graph="$data/$name.txt"
    if [ ! -e "$graph" ]; then
        log "$name: $graph não existe, pulando"
        continue
    fi
    amostra=$(amostra_de "$name")
    log "$name: relatório com caminhos (cos_part3)"
    "$part3" "$graph" "$results/$name.relatorio.txt" direcionado >/dev/null
    log "$name: cos_bench3 (rodadas=$runs, threads=$ncpu, bf-amostra=$amostra, fw-rodadas=$fw_runs)"
    "$bench" "$graph" direcionado "$runs" --fw --fw-rodadas "$fw_runs" \
        --fw-limite-gib "$fw_limit" --bf-todos --bf-amostra "$amostra" \
        --threads "$ncpu" >"$results/$name.txt"
    log "$name: pronto -> $results/$name.txt"
done
log "fim"
