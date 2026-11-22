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
- No W₁ (fortemente conexo): {{W_1.bf_r}} rodadas, ~{{W_1.bf_t}}; toda distância é −∞. Floyd-Warshall leva ~{{W_1.fw}} (diagonal negativa).

## 6. Floyd-Warshall (0:55) — Hygor
- Uma matriz só, atualizada no lugar: 12·V² bytes. Blocos de 64×64 cabem no L1; {{THREADS}} threads; sai cedo se a diagonal fica negativa.
- Gráfico: W₃ precisa de {{W_3.fw_mem}}, W₄ de {{W_4.fw_mem}}, W₅ de {{W_5.fw_mem}}, contra {{RAM_GIB}} GiB de RAM.
- Por isso, do W₃ em diante a tabela 5×5 vem do Bellman-Ford (um por destino). Dizer isso explicitamente.

## 7. Q1 (0:30) — Felipe
- Tabela 10/20/30 → 100. W₁: −∞. W₂: {{W_2.d10}}, {{W_2.d20}}, {{W_2.d30}}. W₃: {{W_3.d10}}, {{W_3.d20}}, {{W_3.d30}}. W₄: {{W_4.d10}}, {{W_4.d20}}, {{W_4.d30}}. W₅: {{W_5.d10}}, {{W_5.d20}}, {{W_5.d30}}.
- Rodadas pequenas perto de V: {{W_2.bf_r}} (W₂), {{W_3.bf_r}} (W₃), {{W_4.bf_r}} (W₄), {{W_5.bf_r}} (W₅). Tempo do Bellman-Ford: {{W_2.bf_t}}, {{W_3.bf_t}}, {{W_4.bf_t}}, {{W_5.bf_t}}.

## 8. Q2 (0:40) — Felipe
- W₂ por Floyd-Warshall; W₃ a W₅ por Bellman-Ford, marcado no slide. W₁: tudo −∞.
- Validação: matriz do Bellman-Ford igual à do Floyd-Warshall em um grafo de 10 mil vértices; W₂ confere com um Dijkstra independente.

## 9. Q3 (0:35) — Felipe
- Médias de 10 execuções, sem leitura. Itálico é estimativa. W₁ é só detecção, não se compara.
- Floyd-Warshall no W₂: {{W_2.fw}} ({{W_2.fw_s}} s, {{THREADS}} threads). Bellman-Ford todos-pares no W₂: {{W_2.ap}} ({{THREADS}} threads), medido.
- W₃ a W₅ em itálico: FW estimado em {{W_3.fw}}, {{W_4.fw}} e ~{{W_5.fw}}; todos-pares em 1 thread, {{W_3.ap}}, {{W_4.ap}} e {{W_5.ap}}.
- Os tempos de W₃ a W₅ vêm de uma segunda passada, com a máquina ociosa.

## 10. Q4 (1:10) — Hygor
- Resultado no W₂ (ambos com {{THREADS}} threads): Bellman-Ford {{W_2.ap}} contra Floyd-Warshall {{W_2.fw}}, ou seja, **Bellman-Ford {{Q4_RAZAO}}× mais rápido**.
- Por quê: FW faz V³ relaxações, esparso ou não (W₂: {{W_2.fw_ops}}). BF todos-pares faz V execuções que só examinam arestas dos ativos; V·R·E é o teto (W₂: {{W_2.bf_ops}}, {{W_2.ops_razao}}× menos que V³; W₃: {{W_3.ops_razao}}×).
- O ganho medido ({{Q4_RAZAO}}×) é menor que o das operações ({{W_2.ops_razao}}×) porque o custo por operação difere: FW acessa a matriz em blocos, de forma sequencial e vetorizada; BF faz acessos irregulares a `dist[]`.
- E o FW ainda precisa de V² de memória: nem roda do W₃ em diante.
- Gráfico em escala log; listrado é estimativa (W₃ a W₅).

## 11. Conclusões (0:25) — Hygor
Três pontos: detecção antecipada de ciclo; BF com ativos vence em grafo esparso; a memória do FW decide.

## Perguntas prováveis

- **Por que Bellman-Ford até um destino usa as arestas que chegam?** A distância de v até t é min sobre arestas v→w de peso + dist(w, t). Partindo de t, quem melhora é o vértice de onde a aresta *sai* para um ativo; achá-lo exige listar as arestas que chegam no ativo.
- **Por que o Floyd-Warshall não roda no W₃?** A matriz tem V² células de 12 bytes: {{W_3.fw_mem}} contra {{RAM_GIB}} GiB de RAM. Armazenar menos exigiria outro algoritmo.
- **Por que o BF todos-pares ganha em grafo esparso?** FW faz V³ operações sempre. BF faz V execuções, cada uma limitada às arestas dos ativos (≤ R·E). No W₂ (E ≈ {{W_2.e_v}}·V, R = {{W_2.bf_r}}), V·R·E = {{W_2.bf_ops}} contra V³ = {{W_2.fw_ops}}; medido, {{Q4_RAZAO}}× mais rápido. Em grafo denso a vantagem encolhe.
- **O tempo estimado é confiável?** FW: V³ exato, calibrado pela média medida do W₂ ({{W_2.fw_s}} s); supõe o mesmo custo por operação, e a matriz maior perde cache, então a estimativa tende a ficar abaixo do real. BF: amostra de destinos ({{W_3.amostra}} no W₃, {{W_4.amostra}} no W₄, {{W_5.amostra}} no W₅), extrapolada; destinos têm custos desiguais.
- **Por que medimos duas vezes?** A primeira passada dos grafos W₃ a W₅ rodou com a máquina ocupada (cerca de 2× mais lenta em uma thread). Refizemos com a máquina ociosa e só usamos a segunda; a primeira fica em `bench/results/parte3/primeira_execucao/` e não entra nos números.
- **Tolerância numérica?** Pesos são `double`; relaxação só vale se melhora por mais que `tolerance` = 8·ε·V·max|w|. Evita ciclos negativos falsos por arredondamento (0,1+0,2−0,3).
- **E se o ciclo negativo não alcança o destino?** `bellman_ford` só vê ciclos de onde t é alcançável; `has_negative_cycle` (origem virtual) vê qualquer ciclo.
- **A comparação é justa ({{THREADS}} threads contra 1)?** O gráfico divide o tempo do BF de 1 thread por {{THREADS}} (escala linear). O BF todos-pares em si é paralelizável por destino sem sincronização.
- **Por que não Johnson ou Dijkstra?** Dijkstra exige pesos não negativos. Johnson está na biblioteca como extra, mas o enunciado compara só BF e FW.
