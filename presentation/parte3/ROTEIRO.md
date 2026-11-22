<!-- gerado por build.py a partir de ROTEIRO.modelo.md; não edite -->
# Roteiro da Parte 3

Tempo total: 7min20 (limite de 8). Os números abaixo vêm de `report/parte3/data.json` e são preenchidos pelo `build.py`; se o JSON for regenerado, rode o build de novo.

| # | Slide | Tempo | Acumulado |
|---|---|---|---|
| 1 | Capa | 0:10 | 0:10 |
| 2 | O pedido e os cinco grafos | 0:35 | 0:45 |
| 3 | Grafo direcionado | 0:40 | 1:25 |
| 4 | Bellman-Ford até o destino | 1:05 | 2:30 |
| 5 | Ciclo negativo | 0:35 | 3:05 |
| 6 | Floyd-Warshall | 0:55 | 4:00 |
| 7 | Q1: distâncias até o 100 | 0:30 | 4:30 |
| 8 | Q2: matriz 5×5 | 0:40 | 5:10 |
| 9 | Q3: tempos médios | 0:35 | 5:45 |
| 10 | Q4: todos os pares | 1:10 | 6:55 |
| 11 | Conclusões | 0:25 | 7:20 |

## 1. Capa (0:10) — Felipe
Título, nomes, repositório.

## 2. O pedido (0:35) — Felipe
- Parte 3: grafos direcionados com pesos negativos, Bellman-Ford até um destino, Floyd-Warshall entre todos os pares.
- Cinco grafos: só o W₁ tem pesos negativos, e tem ciclo negativo; W₂ a W₅ não têm.
- Estudo de caso: 4 perguntas (Q1 a Q4), que respondemos nos slides 7 a 10.

## 3. Grafo direcionado (0:40) — Felipe
- A direção é parâmetro de execução. A CSR guarda duas listas: `forward_` (saem) e `backward_` (chegam).
- BFS, DFS e Dijkstra usam as que saem. Bellman-Ford até o destino usa as que chegam.
- Sem direção, as duas listas coincidem e a segunda não é alocada.

## 4. Bellman-Ford até o destino (1:05) — Hygor
- Distância de todos *até* t: a rodada parte de t e relaxa as arestas que chegam nos ativos; `next` forma a árvore com raiz em t.
- Exemplo: ativos {t}, {1,2}, {3,4}, {5}, vazio. Quatro rodadas, e a lista só encolhe.
- Otimização 1: rodada sem mudança para. Otimização 2: só quem mudou fica ativo.
- Código: a comparação com `tolerance` e o `upcoming.push_back` são os dois pontos que importam.

## 5. Ciclo negativo (0:35) — Hygor
- Sem ciclo, V−1 rodadas bastam; passar disso prova o ciclo. Detectamos antes: ciclo entre os `next`, ou o destino melhora.
- No W₁ (fortemente conexo): 4 rodadas, ~102 µs; toda distância é −∞. Floyd-Warshall leva ~603 ms (diagonal negativa).

## 6. Floyd-Warshall (0:55) — Hygor
- Uma matriz só, atualizada no lugar: 12·V² bytes. Blocos de 64×64 cabem no L1; 11 threads; sai cedo se a diagonal fica negativa.
- Gráfico: W₃ precisa de 120 GB, W₄ de 12 TB, W₅ de 1,2 PB, contra 36 GiB de RAM.
- Por isso, do W₃ em diante a tabela 5×5 vem do Bellman-Ford (um por destino). Dizer isso explicitamente.

## 7. Q1 (0:30) — Felipe
- Tabela 10/20/30 → 100. W₁: −∞. W₂: 10,47, 8,48, 8,71. W₃: 4,63, 5,42, 4,67. W₄: 9,04, 8,83, 9,23. W₅: 37,85, 42,63, 37,86.
- Rodadas pequenas perto de V: 24 (W₂), 25 (W₃), 36 (W₄), 42 (W₅). Tempo do Bellman-Ford: 12,3 ms, 103 ms, 1,47 s, 6,11 s.

## 8. Q2 (0:40) — Felipe
- W₂ por Floyd-Warshall; W₃ a W₅ por Bellman-Ford, marcado no slide. W₁: tudo −∞.
- Validação: matriz do Bellman-Ford igual à do Floyd-Warshall em um grafo de 10 mil vértices; W₂ confere com um Dijkstra independente.

## 9. Q3 (0:35) — Felipe
- Médias de 10 execuções, sem leitura. Itálico é estimativa. W₁ é só detecção, não se compara.
- Floyd-Warshall no W₂: 8,31 min (499 s, 11 threads). Bellman-Ford todos-pares no W₂: 38,1 s (11 threads), medido.
- W₃ a W₅ em itálico: FW estimado em 8,87 h, 1,01 anos e ~1.012 anos; todos-pares em 1 thread, 2,89 h, 14,4 dias e 2,05 anos.
- Os tempos de W₃ a W₅ vêm de uma segunda passada, com a máquina ociosa.

## 10. Q4 (1:10) — Hygor
- Resultado no W₂ (ambos com 11 threads): Bellman-Ford 38,1 s contra Floyd-Warshall 8,31 min, ou seja, **Bellman-Ford 13× mais rápido**.
- Por quê: FW faz V³ relaxações, esparso ou não (W₂: 1,56·10¹³). BF todos-pares faz V execuções que só examinam arestas dos ativos; V·R·E é o teto (W₂: 4,95·10¹¹, 32× menos que V³; W₃: 66×).
- O ganho medido (13×) é menor que o das operações (32×) porque o custo por operação difere: FW acessa a matriz em blocos, de forma sequencial e vetorizada; BF faz acessos irregulares a `dist[]`.
- E o FW ainda precisa de V² de memória: nem roda do W₃ em diante.
- Gráfico em escala log; listrado é estimativa (W₃ a W₅).

## 11. Conclusões (0:25) — Hygor
Três pontos: detecção antecipada de ciclo; BF com ativos vence em grafo esparso; a memória do FW decide.

## Perguntas prováveis

- **Por que Bellman-Ford até um destino usa as arestas que chegam?** A distância de v até t é min sobre arestas v→w de peso + dist(w, t). Partindo de t, quem melhora é o vértice de onde a aresta *sai* para um ativo; achá-lo exige listar as arestas que chegam no ativo.
- **Por que o Floyd-Warshall não roda no W₃?** A matriz tem V² células de 12 bytes: 120 GB contra 36 GiB de RAM. Armazenar menos exigiria outro algoritmo.
- **Por que o BF todos-pares ganha em grafo esparso?** FW faz V³ operações sempre. BF faz V execuções, cada uma limitada às arestas dos ativos (≤ R·E). No W₂ (E ≈ 33·V, R = 24), V·R·E = 4,95·10¹¹ contra V³ = 1,56·10¹³; medido, 13× mais rápido. Em grafo denso a vantagem encolhe.
- **O tempo estimado é confiável?** FW: V³ exato, calibrado pela média medida do W₂ (499 s); supõe o mesmo custo por operação, e a matriz maior perde cache, então a estimativa tende a ficar abaixo do real. BF: amostra de destinos (200 no W₃, 30 no W₄, 10 no W₅), extrapolada; destinos têm custos desiguais.
- **Por que medimos duas vezes?** A primeira passada dos grafos W₃ a W₅ rodou com a máquina ocupada (cerca de 2× mais lenta em uma thread). Refizemos com a máquina ociosa e só usamos a segunda; a primeira fica em `bench/results/parte3/primeira_execucao/` e não entra nos números.
- **Tolerância numérica?** Pesos são `double`; relaxação só vale se melhora por mais que `tolerance` = 8·ε·V·max|w|. Evita ciclos negativos falsos por arredondamento (0,1+0,2−0,3).
- **E se o ciclo negativo não alcança o destino?** `bellman_ford` só vê ciclos de onde t é alcançável; `has_negative_cycle` (origem virtual) vê qualquer ciclo.
- **A comparação é justa (11 threads contra 1)?** O gráfico divide o tempo do BF de 1 thread por 11 (escala linear). O BF todos-pares em si é paralelizável por destino sem sincronização.
- **Por que não Johnson ou Dijkstra?** Dijkstra exige pesos não negativos. Johnson está na biblioteca como extra, mas o enunciado compara só BF e FW.
