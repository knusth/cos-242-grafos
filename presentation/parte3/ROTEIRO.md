# Roteiro de Apresentação — Parte 3 (8 minutos · 12 slides + 2 apêndices)

**Disciplina:** COS242 — Teoria dos Grafos (Poli / UFRJ)  
**Autores:** Felipe Marroni · Hygor Knust · **Professor:** Daniel Ratton Figueiredo  
**Ritmo alvo:** ~120 palavras/minuto (~960 palavras no roteiro principal = **8:00**)  
**Estrutura narrativa (DAG sem referências antecipadas):**
1. **Ato 1 — O Problema & Bellman-Ford (Slides 1–4):** escala dos grafos → *como* BF evita trabalho (lista de ativos + parada) → ciclos negativos e precisão IEEE-754.
2. **Ato 2 — Todos os Pares & Hardware (Slides 5–7):** BF vs. FW (`13×`) → *por quê* (`211×` menos ops ÷ `16×` mais caro/op) → efeito da cache L2 em 10M vértices.
3. **Ato 3 — Algoritmo de Johnson (Slides 8–9):** *por que* somar constante falha vs. potencial telescópico `h` → fila radix e benchmark `2,4×` sobre BF.
4. **Ato 4 — Paralelismo & Síntese (Slides 10–12):** destinos independentes vs. blocos `64×64` → P/E-cores e parede da L2 → matriz de decisão.

---

## Slide 1 · Capa (0:00 – 0:25 · ~50 palavras)

Bom dia a todos. Hoje apresentamos a Parte 3 do trabalho de Grafos: caminhos mínimos com pesos negativos em grafos direcionados de até dez milhões de vértices, implementados do zero em `C++20` no Apple M3 Pro.

À direita, o exemplo de seis vértices ilustra nossa convenção: calculamos distâncias até um destino fixo guardando a árvore `next_`, destacando em vermelho a aresta negativa `3 → 6` de peso `−4`.

---

## Slide 2 · Cinco grafos e o limite de memória (0:25 – 1:05 · ~80 palavras)

Trabalhamos com cinco grafos, de $W_1$ e $W_2$ com 25 mil vértices até $W_5$ com 10 milhões de vértices e 40 milhões de arestas. Apenas $W_1$ possui pesos negativos (`−5` a `10`).

Para rodar Bellman-Ford direcionado ao destino, armazenamos as arestas de entrada em CSR reverso (`backward_`), ocupando de `13,4 MB` no $W_1$ a `1,04 GB` no $W_5$. Já a matriz densa de Floyd-Warshall (`12·V²` bytes) exige `7,5 GB` no $W_2$, mas explode para `120 GB` no $W_3$ e `1,2 PB` no $W_5$ — esbarrando imediatamente nos `16 GiB` de limite e nos `36 GiB` de RAM da máquina.

---

## Slide 3 · Como o Bellman-Ford evita trabalho inútil (1:05 – 1:50 · ~85 palavras)

Antes dos benchmarks, vale entender como tornamos o Bellman-Ford rápido na prática. O algoritmo clássico faz `V − 1` rodadas fixas varrendo todas as `E` arestas — `20,6 bilhões` de relaxações por destino no $W_2$.

Usamos duas otimizações simples e exatas: primeiro, a **lista de ativos** (`active[]`), que guarda apenas os vértices cuja distância realmente diminuiu na rodada anterior — quem não mudou não pode melhorar seus predecessores; segundo, a **parada antecipada**, encerrando assim que `active[]` esvazia. No $W_2$ (à direita), a onda começa no destino `100`, atinge pico de `78%` na rodada 7 e zera na rodada `24` — examinando cada aresta apenas `3,6×` no total.

---

## Slide 4 · Ciclos negativos e precisão numérica (1:50 – 2:35 · ~85 palavras)

E se houver ciclo negativo, como no $W_1$? Lá, `9,1%` das arestas têm inversa e existem `2.446` ciclos negativos de 2 arestas, como `5438 ↔ 1268` de soma `−1,34`. Em vez de esperar `24.999` rodadas, nosso `has_cycle` persegue os ponteiros `next_` apenas dos vértices alterados usando carimbos monotônicos (`stamps`), fechando o ciclo em `O(V)` já na rodada 4, em `0,10 ms`.

Há também uma armadilha em ponto flutuante: em `double` IEEE-754, `(0,1 + 0,2) − 0,3` sobra `5,55×10⁻¹⁷`, gerando falsas melhorias de `1 ulp` e laços espúrios em `next_`. Exigir melhora acima de `tolerance = 8·ε·V·max|w|` elimina falsos ciclos sem perder precisão.

---

## Slide 5 · Todos os pares: Bellman-Ford vence por 13× (2:35 – 3:10 · ~70 palavras)

Passando a todos os pares: no $W_2$, único grafo onde ambos cabem na memória, o Bellman-Ford com 11 threads leva `38,1 s` contra `498,7 s` do Floyd-Warshall em blocos — **13,1× mais rápido**. Mesmo em 1 thread (`327,5 s`), o BF já bate o FW paralelo.

Na extrapolação à direita (mantendo 1T do BF separado de 11T do FW), igualando threads a vantagem cresce de `34×` no $W_3$ para `280×` no $W_4$ e `5.400×` no $W_5$.

---

## Slide 6 · Por que 211× menos operações viram 13× (3:10 – 3:55 · ~85 palavras)

Este gráfico separa exatamente o que aconteceu no $W_2$ em dois painéis independentes.

À esquerda, o **volume de operações** por destino: o BF clássico faria `20,6 bilhões` de relaxações (`33×` pior que os `625 milhões` de $V^2$ do FW). Com parada antecipada e lista de ativos, nosso BF cai para `2,97 milhões` — **211× menos operações** que o FW.

À direita, o **custo de hardware por operação**: cada relaxação do FW lê blocos contíguos na L1 vetorizados em NEON (`0,35 ns`), enquanto o BF faz saltos aleatórios no CSR (`5,66 ns` — **16× mais caro**). Dividindo `211` por `16,1`, chegamos exatamente aos **13,1×** medidos no relógio.

---

## Slide 7 · O efeito do cache em 10 milhões de vértices (3:55 – 4:35 · ~75 palavras)

Quando escalamos o Bellman-Ford de $W_2$ até $W_5$, a memória volta a dominar. O estado por execução (`dist + next`, `12·V` bytes) cresce de `0,3 MB` no $W_2$ para `120 MB` no $W_5$, ultrapassando os `16 MiB` da cache L2.

O impacto é imediato nos dois painéis: o custo por aresta relaxada salta `14,6×` (de `2,51` para `36,71 ns`), e a perseguição de ponteiros em `has_cycle` — que custava só `3%` a `8%` em $W_2$–$W_4$ — explode para **36,4%** do tempo total no $W_5$ (`2,52 s` de `6,92 s`).

---

## Slide 8 · Johnson: por que somar constante falha (4:35 – 5:20 · ~90 palavras)

Indo além da especificação, implementamos o **algoritmo de Johnson** para baixar aquelas `3,6` passagens do BF para **uma única passagem** com Dijkstra — mesmo havendo pesos negativos.

Mas atenção a um erro clássico: **não basta somar o menor peso `+2` a todas as arestas**. No triângulo do meio, o ótimo real `A → B → C` (custo `0`, 2 arestas) paga `+4` e vira `4`, enquanto `A → C` (1 aresta) paga só `+2` e vira `3` — invertendo o caminho mínimo!

A sacada de Johnson (à direita) é reponderar por um **potencial de vértice** $h$: `w'(u,v) = w(u,v) + h(v) − h(u) ≥ 0`. Ao somar ao longo de qualquer caminho `s → t`, todos os `h` intermediários cancelam telescopicamente, deslocando todos os caminhos pelo mesmo `h(t) − h(s)` — preservando 100% a ordem ótima.

---

## Slide 9 · Johnson na prática: fila radix acelera 2,4× (5:20 – 6:00 · ~75 palavras)

Para que o Dijkstra dentro do Johnson compense contra o BF enxuto, substituímos o heap binário por uma **fila radix de 65 baldes**. Como `bit_cast<uint64_t>` preserva a ordem de `double ≥ 0`, o balde é dado em uma instrução por `bit_width(key ^ last)`. Inserções são `O(1)` e cada chave só desce de balde quando `B0` esvazia.

Na mesma sessão ociosa no $W_2$ (11 threads): BF marca `30,0 s`, Johnson com heap binário cai para `19,5 s` (`1,5×`) e com fila radix chega a **`12,33 s`** (**2,4× mais rápido** que o BF, perto do teto teórico sem fila de `8,4 s`).

---

## Slide 10 · Paralelismo: destinos independentes vs. blocos (6:00 – 6:40 · ~75 palavras)

Como paralelizar? No BF e no Johnson, particionar o grafo por vértices cortaria `91%` das arestas (já que `|u − v| ≈ V/3`). Em vez disso, mantemos o CSR somente leitura e cada thread retira blocos dinâmicos de `16` destinos via `fetch_add` atômico, usando um espaço local de `12·V` bytes — sem travas e balanceando automaticamente núcleos rápidos e lentos.

Já no Floyd-Warshall, usamos blocagem `64×64` (`48 KiB` na L1) em três fases sincronizadas por `std::barrier` (`1.173` barreiras vs. `25.000`), com o laço interno `relax_segment` sem desvios para auto-vetorização NEON.

---

## Slide 11 · Escala nos P/E-cores e saturação da L2 (6:40 – 7:20 · ~80 palavras)

O Apple M3 Pro tem 5 núcleos de desempenho (P) e 6 de eficiência (E), onde cada E-core vale `r ≈ 0,29` de um P-core — teto teórico de `5 + 6·r = 6,7×`.

Quando o grafo cabe na cache (`aleatorio5000`, à esquerda), BF, FW e Johnson escalam juntos até `5,9×–6,4×`. Nos grafos do trabalho à direita, o $W_2$ (`0,3 MB/thread`) atinge `7,2×`. Já no $W_4$ (`12 MB/thread`), a partir de **2 threads** (`24 MB`) o trabalho ultrapassa a L2 de `16 MiB` e a escala cai para `4,2×`; no $W_5$ (`120 MB/thread`), o barramento DRAM satura em `2,4×`.

---

## Slide 12 · Qual algoritmo escolher em cada cenário (7:20 – 8:00 · ~75 palavras)

Fechando com a matriz de decisão:
1. **1 destino esparso** (com ou sem pesos negativos): BF com lista de ativos e `next_` (`0,10 ms` no $W_1$, `6,11 s` no $W_5$);
2. **Todos os pares esparso**: Johnson + fila radix vence com folga (`12,3 s` no $W_2$, `2,4×` sobre BF e `40×` sobre FW), ou BF paralelo se a memória for estrita;
3. **Grafos densos e pequenos**: Floyd-Warshall em blocos `64×64` com NEON (`0,35 ns/op`).

A lição central: esparsidade algorítmica e engenharia de memória ditam o desempenho real muito além da notação assintótica. Obrigado — ficamos à disposição para perguntas.

---

## Guia de Defesa para Perguntas (Q&A · Apêndices A1 e A2)

- **Apêndice A1 (Validação e distâncias exatas):**
  - Todas as distâncias `{10, 20, 30} → 100` e a matriz `5×5` do $W_2$ (`10..50`) foram validadas com 100% de concordância contra um Dijkstra independente em Python; nos 4 algoritmos todos-pares no $W_2$, o checksum coincide exatamente em `28,02`.
  - No $W_1$, todas as distâncias são `−∞` porque o grafo é fortemente conexo e contém `2.446` ciclos negativos de 2 arestas.
- **Apêndice A2 (Detalhes de código em `include/cos/graph.hpp`):**
  - *Por que `has_cycle` é `O(V)` amortizado?* Cada vértice visitado recebe o selo `walk` atual ou encontra um selo `>= first_stamp` de outra caminhada na mesma rodada e interrompe imediatamente.
  - *Por que o potencial $h$ em Johnson tem sinal `w + h(v) − h(u)`?* Porque nosso Bellman-Ford é direcionado ao destino (grafo reverso `backward_`): definimos $h(u) = d(u \to q)$ até o vértice virtual $q$. Pela desigualdade triangular, $h(u) \le w(u,v) + h(v) \implies w'(u,v) = w(u,v) + h(v) - h(u) \ge 0$. (Na formulação clássica a partir de uma origem $q$, $h(v) = d(q \to v)$ e o sinal inverte para $w + h(u) - h(v)$ — ambos dão exatamente a mesma soma telescópica!)
  - *Por que `RadixFrontier` funciona com `double`?* Números IEEE-754 não negativos em `double` têm a mesma ordem lexicográfica como `uint64_t` após normalizar `-0.0` para `+0.0`. `std::bit_width(key ^ last_)` retorna em 1 instrução (`clz`) o bit mais significativo divergente (`0..64`).
  - *Por que o BF no Slide 5 marca `38,1 s` e no Slide 9 marca `30,0 s`?* O Slide 5 vem da suíte principal (rodada sob carga de fundo do sistema); no Slide 9, BF, Johnson Heap e Johnson Radix foram executados em sequência na mesma sessão ociosa para comparação justa (`2,4×`).
