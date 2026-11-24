# Relatório da Parte 3

## Reconstruir o PDF

A partir da raiz do repositório (usando os dados já coletados em `report/parte3/*.json` e `bench/results/parte3/`):

```sh
python3 -I report/parte3/tabelas.py
(cd report/parte3 && tectonic relatorio.tex)
```

Com o cache local do Tectonic já preenchido, também é possível compilar offline com `tectonic --only-cached relatorio.tex`.

Se novos resultados forem gerados por `bench/parte3/run_part3.sh` ou pelos scripts auxiliares, regenere antes os JSONs:

```sh
python3 -I bench/parte3/summarize_p3.py   # bench/results/parte3/* -> report/parte3/data.json
python3 -I report/parte3/grafos.py        # data/p3_W_1..5.txt -> report/parte3/grafos.json
python3 -I report/parte3/w1_ciclos.py     # data/p3_W_1.txt -> report/parte3/w1_ciclos.json
python3 -I report/parte3/exemplo.py       # gera exemplo.json e tests/fixtures/exemplo_p3*.txt
python3 -I report/parte3/tabelas.py       # gera report/parte3/tabelas.tex e valida consistência
(cd report/parte3 && tectonic relatorio.tex)
```

## Arquivos

| Arquivo | Função |
|---|---|
| `relatorio.tex`, `relatorio.pdf` | Fonte LaTeX e PDF final (6 páginas, 0 Overfull) |
| `tabelas.py`, `tabelas.tex` | Gera as macros `\dado{chave}`, figuras PGF/TikZ e tabelas a partir dos JSONs e de `bench/results/parte3/` |
| `data.json` | Resumo principal das execuções de `bench/parte3/run_part3.sh` (gerado por `bench/parte3/summarize_p3.py`); também alimenta os slides |
| `contagens.json` | Contagens por rodada e todos-os-pares do Bellman-Ford (gerado por `bench/parte3/contagem_bf.cpp`) |
| `tempo_busca_ciclo.json` | Tempo gasto na busca de ciclo em `next` (gerado por `bench/parte3/tempo_busca_ciclo.cpp`) |
| `grafos.py`, `grafos.json` | Caracterização estrutural de $W_1$–$W_5$ (graus, pesos, reciprocidade, conexidade forte, saltos) |
| `w1_ciclos.py`, `w1_ciclos.json` | Arestas negativas, ciclos negativos de 2 arestas e conexidade forte em $W_1$ |
| `exemplo.py`, `exemplo.json` | Grafo de exemplo (6 vértices) e variante com ciclo negativo, com execução conferida via `cos_part3` |

## Verificações automáticas de `tabelas.py`

- Compara o $W_2$ com as distâncias de referência e imprime `DIVERGÊNCIA W_2: ...` em `stderr` se houver diferença.
- Lê constantes e número de barreiras (`fw_block`, `sync.arrive_and_wait()`) diretamente de `include/cos/graph.hpp`.
- Confere a cadeia de fatores entre Floyd-Warshall e Bellman-Ford ($33\times \div 1.149 \div 6{,}05 \times 16 \approx 1/13$, tolerância de 1 %), a escala com threads (`bench/results/parte3/escala_*.txt`, `maquina.txt`, `nucleo_eficiencia.txt`) e os ganhos do algoritmo de Johnson (`p3_W_2.{bf_todos,johnson_heap,johnson_radix}.txt`).
- Todo número citado em `relatorio.tex` vem de `\dado{chave}`, garantindo consistência entre texto, tabelas, figuras e os slides em `presentation/parte3/`.
