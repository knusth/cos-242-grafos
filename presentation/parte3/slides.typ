// =============================================================================
// COS242 — Teoria dos Grafos (Poli / UFRJ)
// Parte 3: Caminhos Mínimos com Pesos Negativos
// Felipe Marroni · Hygor Knust · Prof. Daniel Ratton Figueiredo
// 12 Slides Principais + 2 Slides de Apêndice (= 14 páginas · 8 minutos)
// =============================================================================

#let c-ink     = rgb("#0f172a")
#let c-navy    = rgb("#1b365d")
#let c-teal    = rgb("#0f6260")
#let c-ochre   = rgb("#b45309")
#let c-crimson = rgb("#9f1239")
#let c-slate   = rgb("#475569")
#let c-muted   = rgb("#64748b")
#let c-soft    = rgb("#f8fafc")
#let c-rule    = rgb("#cbd5e1")
#let c-hair    = rgb("#e2e8f0")

#set page(
  width: 297mm,
  height: 167.0625mm,
  margin: (left: 15mm, right: 15mm, top: 13mm, bottom: 13mm),
  footer-descent: 3.0mm,
  fill: white,
  footer: context {
    let p = counter(page).get().first()
    if p > 1 {
      line(length: 100%, stroke: 0.45pt + c-hair)
      v(1.6mm)
      grid(
        columns: (1fr, auto),
        text(size: 8pt, fill: c-muted, [COS242 · Teoria dos Grafos — UFRJ · Felipe Marroni & Hygor Knust]),
        if p <= 12 {
          text(size: 8pt, weight: "bold", fill: c-navy, [#p / 12])
        } else {
          text(size: 8pt, weight: "bold", fill: c-muted, [Apêndice · Q&A])
        }
      )
    }
  },
)

#set text(font: "Helvetica Neue", size: 9.8pt, fill: c-ink, lang: "pt")
#show math.equation: set text(font: "New Computer Modern Math")
#show raw: set text(font: "Menlo", size: 8.0pt)

// ── Primitivas editoriais ─────────────────────────────────────────────────────

#let slide-head(sec, title, sub: none) = {
  block(width: 100%, below: 3.2mm)[
    #grid(
      columns: (1fr, auto),
      align: bottom,
      text(size: 16pt, weight: "bold", fill: c-ink, title),
      text(size: 8.2pt, weight: "semibold", fill: c-muted, sec),
    )
    #if sub != none {
      v(0.7mm)
      text(size: 9.2pt, fill: c-slate, sub)
    }
    #v(1.4mm)
    #line(length: 100%, stroke: 0.8pt + c-navy)
  ]
}

#let card(body, accent: c-navy, bg: c-soft, inset-val: 3.2mm) = {
  rect(
    width: 100%,
    fill: bg,
    stroke: (left: 2.4pt + accent, top: 0.5pt + c-hair, right: 0.5pt + c-hair, bottom: 0.5pt + c-hair),
    radius: (right: 1.5pt),
    inset: inset-val,
    body,
  )
}

#let code-box(file-lbl, code-block, accent: c-navy) = {
  block(
    width: 100%,
    fill: c-soft,
    stroke: (top: 2.2pt + accent, left: 0.5pt + c-rule, right: 0.5pt + c-rule, bottom: 0.5pt + c-rule),
    radius: (bottom: 1.5pt),
    inset: (x: 3.0mm, y: 2.6mm),
  )[
    #text(size: 7.8pt, weight: "bold", fill: accent, font: "Menlo", file-lbl)
    #v(1.2mm)
    #line(length: 100%, stroke: 0.4pt + c-hair)
    #v(1.2mm)
    #code-block
  ]
}

// =============================================================================
// SLIDE 1 · CAPA (SPLIT 52 / 48)
// =============================================================================
#page(margin: 0mm, footer: none)[
  #grid(
    columns: (52%, 48%),
    rows: (167.0625mm,),
    pad(left: 15mm, right: 11mm, top: 17mm, bottom: 14mm)[
      #text(size: 8.4pt, weight: "bold", fill: c-navy, tracking: 1.0pt, [COS242 · TEORIA DOS GRAFOS · POLI / UFRJ])
      #v(2.2mm)
      #line(length: 22mm, stroke: 1.8pt + c-navy)
      #v(7.5mm)
      #par(leading: 0.52em)[#text(
        font: "Libertinus Serif",
        size: 24.5pt,
        weight: "bold",
        fill: c-ink,
        [Caminhos Mínimos\ com Pesos\ Negativos],
      )]
      #v(5.0mm)
      #par(leading: 0.55em)[#text(size: 10.2pt, fill: c-slate, [
        Bellman-Ford, Floyd-Warshall, Johnson e paralelismo em grafos de até 10 milhões de vértices (`C++20` · Apple M3 Pro).
      ])]
      #v(7.5mm)
      #text(size: 10.2pt, weight: "bold", fill: c-ink, [Felipe Marroni · Hygor Knust]) \
      #v(0.5mm)
      #text(size: 9.0pt, fill: c-muted, [Prof. Daniel Ratton Figueiredo · Parte 3])
      #v(1fr)
      #line(length: 100%, stroke: 0.6pt + c-rule)
      #v(4.0mm)
      #grid(
        columns: (1fr, 1fr, 1fr),
        gutter: 4mm,
        [
          #text(size: 13.5pt, weight: "bold", fill: c-teal, [13× mais rápido]) \
          #text(size: 8.2pt, fill: c-muted, [BF sobre FW no $W_2$ (11T)])
        ],
        [
          #text(size: 13.5pt, weight: "bold", fill: c-ochre, [2,4× sobre BF]) \
          #text(size: 8.2pt, fill: c-muted, [Johnson + fila radix ($W_2$)])
        ],
        [
          #text(size: 13.5pt, weight: "bold", fill: c-navy, [10M vértices]) \
          #text(size: 8.2pt, fill: c-muted, [1 destino em 6,1 s · CSR])
        ],
      )
    ],
    box(width: 100%, height: 100%, fill: c-soft, stroke: (left: 0.7pt + c-rule), inset: 5mm)[
      #align(center + horizon)[
        #image("assets/fig_01_cover_graph.svg", width: 100%)
      ]
    ],
  )
]

// =============================================================================
// SLIDE 2 · CINCO GRAFOS E O LIMITE DE MEMÓRIA
// =============================================================================
#page[
  #slide-head("1 · O Desafio", "Cinco grafos e o limite de memória")
  #grid(
    columns: (53%, 45%),
    gutter: 2%,
    [
      #set table(
        stroke: (x, y) => if y == 0 { (bottom: 1.0pt + c-navy) } else { (bottom: 0.45pt + c-hair) },
        inset: (x: 4.5pt, y: 5.5pt),
        align: (left, right, right, center, right, right, right),
      )
      #text(size: 8.6pt, [
        #table(
          columns: (auto, auto, auto, auto, auto, auto, auto),
          table.header(
            [*Grafo*], [*$V$*], [*$E$*], [*Pesos*], [*CSR rev.*], [*FW $12 V^2$*], [*BF→100*],
          ),
          [*$W_1$*], [25 mil], [550 mil], text(fill: c-crimson, weight: "bold")[−5 a 10], [13,4 MB], [7,5 GB], text(fill: c-crimson, weight: "bold")[0,10 ms],
          [*$W_2$*], [25 mil], [825 mil], [0 a 10], [20,0 MB], [7,5 GB], [12,3 ms],
          [*$W_3$*], [100 mil], [6,1 mi], [0 a 10], [147 MB], text(fill: c-crimson, weight: "bold")[120 GB], [103 ms],
          [*$W_4$*], [1 mi], [31,0 mi], [0 a 10], [752 MB], text(fill: c-crimson, weight: "bold")[12 TB], [1,47 s],
          [*$W_5$*], [10 mi], [40,0 mi], [0 a 10], [1,04 GB], text(fill: c-crimson, weight: "bold")[1,2 PB], [6,11 s],
        )
      ])
      #v(4mm)
      #card(accent: c-teal, inset-val: 3.4mm)[
        #text(size: 9.1pt, weight: "bold", fill: c-teal, [Por que armazenar o grafo em CSR reverso (`backward_`)?])
        #v(1.2mm)
        #text(size: 8.8pt, fill: c-slate, [
          No Bellman-Ford direcionado ao destino $t$, as melhorias propagam-se de trás para frente, de cada vértice para seus predecessores $u arrow v$. Guardar as arestas de entrada em CSR contíguo (`offsets`, `neighbors`, `weights`) cabe em *1,04 GB* no $W_5$ — enquanto a matriz densa do Floyd-Warshall exigiria *1,2 PB* ($O(V^2)$).
        ])
      ]
      #v(2.5mm)
      #text(size: 8.2pt, fill: c-muted, [
        Apple M3 Pro · 36 GiB RAM · `clang 21 -O3`. `BF→100`: média de 10 execuções (1T); FW bloqueado a partir de $W_3$ (limite de 16 GiB).
      ])
    ],
    [
      #image("assets/fig_02_ram_cliff.svg", width: 100%)
    ],
  )
]

// =============================================================================
// SLIDE 3 · COMO O BELLMAN-FORD EVITA TRABALHO INÚTIL (LISTA DE ATIVOS)
// =============================================================================
#page[
  #slide-head(
    "1 · Bellman-Ford",
    "Como o Bellman-Ford evita trabalho inútil",
    sub: [Em vez de varrer todas as $E$ arestas em $V - 1$ rodadas, propagamos apenas os vértices cuja distância mudou na rodada anterior.],
  )
  #image("assets/fig_03_bf_ativos.svg", width: 100%)
]

// =============================================================================
// SLIDE 4 · CICLOS NEGATIVOS E PRECISÃO NUMÉRICA
// =============================================================================
#page[
  #slide-head(
    "1 · Ciclos & Precisão",
    "Ciclos negativos e precisão numérica",
    sub: [Detecção $O(V)$ por perseguição de ponteiros no vetor `next_` e margem contra arredondamento IEEE-754 em `double`.],
  )
  #image("assets/fig_03_cycle_precision.svg", width: 100%)
]

// =============================================================================
// SLIDE 5 · TODOS OS PARES: BELLMAN-FORD VENCE POR 13×
// =============================================================================
#page[
  #slide-head(
    "2 · Todos os Pares",
    "Todos os pares: Bellman-Ford vence por 13×",
    sub: [Comparação direta no $W_2$ (medido) e projeção assintótica em $W_3$–$W_5$ mantendo contagens de threads separadas.],
  )
  #image("assets/fig_04_apsp_times.svg", width: 100%)
]

// =============================================================================
// SLIDE 6 · POR QUE 211× MENOS OPERAÇÕES VIRAM 13×
// =============================================================================
#page[
  #slide-head(
    "2 · Anatomia do Ganho",
    "Por que 211× menos operações viram 13×",
    sub: [Balanço no $W_2$ (25k vértices · 11 threads): o corte no volume de relaxações (lista de ativos + parada) versus o custo na CPU.],
  )
  #image("assets/fig_05_waterfall.svg", width: 100%)
]

// =============================================================================
// SLIDE 7 · O EFEITO DO CACHE EM 10 MILHÕES DE VÉRTICES
// =============================================================================
#page[
  #slide-head(
    "2 · Memória & Cache",
    "O efeito do cache em 10 milhões de vértices",
    sub: [Quando o estado por execução ($12 dot V$ bytes de `dist` + `next`) ultrapassa os 16 MiB de L2, a latência salta 14,6×.],
  )
  #image("assets/fig_06_wave_cache.svg", width: 100%)
]

// =============================================================================
// SLIDE 8 · JOHNSON: POR QUE SOMAR CONSTANTE FALHA
// =============================================================================
#page[
  #slide-head(
    "3 · Algoritmo de Johnson",
    "Johnson: por que somar constante falha",
    sub: [Para rodar Dijkstra com pesos negativos, somar uma constante penaliza caminhos com mais arestas; o potencial $h$ preserva o ótimo.],
  )
  #image("assets/fig_07_johnson_radix.svg", width: 100%)
]

// =============================================================================
// SLIDE 9 · JOHNSON NA PRÁTICA: FILA RADIX ACELERA 2,4×
// =============================================================================
#page[
  #slide-head(
    "3 · Johnson na Prática",
    "Johnson na prática: fila radix acelera 2,4×",
    sub: [Fila de prioridade monótona em 65 baldes (`bit_width(key ^ last)`) e benchmark todos-os-pares no $W_2$ (11 threads).],
  )
  #image("assets/fig_08_johnson_bench.svg", width: 100%)
]

// =============================================================================
// SLIDE 10 · PARALELISMO: DESTINOS INDEPENDENTES VS. BLOCOS
// =============================================================================
#page[
  #slide-head(
    "4 · Paralelismo",
    "Paralelismo: destinos independentes vs. blocos",
    sub: [Sem particionar o grafo (91% de corte), BF e Johnson distribuem destinos via `fetch_add(16)`; FW usa blocos $64 times 64$ com NEON.],
  )
  #image("assets/fig_09_parallel_arch.svg", width: 100%)
]

// =============================================================================
// SLIDE 11 · ESCALA NOS P/E-CORES E SATURAÇÃO DA L2
// =============================================================================
#page[
  #slide-head(
    "4 · Escala em Hardware",
    "Escala nos P/E-cores e saturação da L2",
    sub: [Assimetria do Apple M3 Pro (5 P-cores + 6 E-cores, $r = 0,29$) e queda de escalabilidade quando $T dot 12 V$ excede a cache L2.],
  )
  #image("assets/fig_10_scaling.svg", width: 100%)
]

// =============================================================================
// SLIDE 12 · QUAL ALGORITMO ESCOLHER EM CADA CENÁRIO
// =============================================================================
#page[
  #slide-head("5 · Síntese", "Qual algoritmo escolher em cada cenário")
  #set table(
    stroke: (x, y) => if y == 0 { (bottom: 1.1pt + c-navy) } else { (bottom: 0.5pt + c-hair) },
    inset: (x: 6pt, y: 7pt),
    align: (left, left, left, left, left),
  )
  #text(size: 8.9pt, [
    #table(
      columns: (21%, 20%, 16%, 22%, 21%),
      table.header(
        [*Regime do grafo*], [*Algoritmo vencedor*], [*Memória*], [*Gargalo real*], [*Resultado medido*],
      ),
      [
        *1 destino, esparso*\ ($w < 0$ ou ciclo)
      ],
      text(weight: "bold", fill: c-teal)[BF + ativos + `next_`],
      [CSR $O(V+E)$\ (13 MB – 1,04 GB)],
      [Localidade em `dist+next`\ (36,4% em `has_cycle` no $W_5$)],
      [*0,10 ms* ($W_1$, para na rod. 4)\ *6,11 s* ($W_5$, $10^7$ vértices)],
      [
        *Todos os pares, esparso*\ ($w < 0$ sem ciclo $<0$)
      ],
      text(weight: "bold", fill: c-ochre)[Johnson + Radix Heap],
      [CSR + $12 V^2$ saída\ (20 MB grafo no $W_2$)],
      [Manutenção da fronteira\ (6,6 ns/op vs. 10,4 ns heap)],
      [*12,3 s* no $W_2$ (11T)\ *2,4×* sobre BF · *40×* sobre FW],
      [
        *Todos os pares, esparso*\ (memória estrita)
      ],
      text(weight: "bold", fill: c-teal)[BF paralelo (`fetch_add`)],
      [CSR + $12 V$ / thread\ (sem matriz $V^2$ se só resp.)],
      [Banda DRAM / L2 de 16 MiB\ quando $T dot 12 V > 16$ MiB],
      [*30,0–38,1 s* no $W_2$ (11T)\ *7,2×* escala ($W_2$) · *4,2×* ($W_4$)],
      [
        *Grafo denso ($E approx V^2$)*\ e $V <= 25$k
      ],
      text(weight: "bold", fill: c-navy)[FW blocos $64 times 64$],
      [Matriz $12 V^2$ (7,5 GB)\ (OOM em $V >= 100$k)],
      [Custo aritmético $V^3$\ (0,35 ns/op com NEON)],
      [*498,7 s* no $W_2$ (11T)\ *5,9×* escala em 5k vértices],
    )
  ])
  #v(5mm)
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 4.5mm,
    card(accent: c-teal, inset-val: 3.4mm)[
      #text(size: 9.4pt, weight: "bold", fill: c-teal, [1. Esparsidade vence $O(V^3)$])
      #v(1.2mm)
      #text(size: 8.6pt, fill: c-slate, [
        Parada antecipada (≈ 22 rodadas) e lista de ativos (3,6×E) reduzem operações em *211×* no $W_2$ — transformando 33× pior teórico em *13×* mais rápido no relógio.
      ])
    ],
    card(accent: c-crimson, inset-val: 3.4mm)[
      #text(size: 9.4pt, weight: "bold", fill: c-crimson, [2. Cache e banda ditam o teto])
      #v(1.2mm)
      #text(size: 8.6pt, fill: c-slate, [
        Acesso aleatório ao `dist` custa *16×* mais por op que blocos L1/NEON (5,7 vs. 0,35 ns). Ao exceder 16 MiB de L2, a escala cai de *7,2×* ($W_2$) para *2,4×* ($W_5$).
      ])
    ],
    card(accent: c-ochre, inset-val: 3.4mm)[
      #text(size: 9.4pt, weight: "bold", fill: c-ochre, [3. Engenharia fecha o último fator])
      #v(1.2mm)
      #text(size: 8.6pt, fill: c-slate, [
        Potencial de Johnson + fila radix de 65 baldes (*2,4×* sobre BF), laços *branchless* para NEON, `fetch_add(16)` em P/E-cores e `tolerance` contra 1 ulp.
      ])
    ],
  )
]

// =============================================================================
// APÊNDICE A1 · DISTÂNCIAS E TEMPOS EXIGIDOS
// =============================================================================
#page[
  #slide-head(
    "Apêndice · Q&A",
    "Distâncias e tempos (W₁–W₅)",
    sub: [Valores conferidos 100% contra Dijkstra independente em Python (`d` = distância mínima até o alvo; tempos = média ± dp em 10 execuções, 1T).],
  )
  #grid(
    columns: (48%, 49%),
    gutter: 3%,
    [
      #text(size: 9.8pt, weight: "bold", fill: c-navy, [A. Origens $\{10, 20, 30\} arrow 100$ e tempo BF (1T)])
      #v(2mm)
      #set table(
        stroke: (x, y) => if y == 0 { (bottom: 1.0pt + c-navy) } else { (bottom: 0.45pt + c-hair) },
        inset: (x: 5pt, y: 5.5pt),
        align: (left, right, right, right, right, right),
      )
      #text(size: 8.6pt, [
        #table(
          columns: (auto, auto, auto, auto, auto, auto),
          table.header(
            [*Grafo*], [*$d(10)$*], [*$d(20)$*], [*$d(30)$*], [*Rod.*], [*BF → 100*],
          ),
          [*$W_1$*],
          text(fill: c-crimson, weight: "bold")[−∞],
          text(fill: c-crimson, weight: "bold")[−∞],
          text(fill: c-crimson, weight: "bold")[−∞],
          [4],
          text(fill: c-crimson, weight: "bold")[0,10 ± 0,05 ms],
          [*$W_2$*], [10,47], [8,48], [8,71], [24], [12,3 ± 1,1 ms],
          [*$W_3$*], [4,63], [5,42], [4,67], [25], [102,7 ± 4,1 ms],
          [*$W_4$*], [9,04], [8,83], [9,23], [36], [1,47 ± 0,05 s],
          [*$W_5$*], [37,85], [42,63], [37,86], [42], [6,11 ± 0,06 s],
        )
      ])
      #v(4mm)
      #card(accent: c-teal, inset-val: 3.0mm)[
        #text(size: 8.8pt, weight: "bold", fill: c-teal, [Tempos todos-pares medidos vs. estimados])
        #v(1.0mm)
        #text(size: 8.4pt, fill: c-slate, [
          • *$W_1$ (ciclo $<0$)*: BF todos-pares = *0,27 ms* (11T); FW = *0,60 s* (11T).\
          • *$W_2$ (25k)*: BF = *38,1 ± 1,8 s* (11T) / *327,5 s* (1T); FW = *498,7 ± 43,6 s* (11T).\
          • *$W_3$ / $W_4$ / $W_5$*: BF 1T (amostra) = *2,89 h* / *14,4 d* / *2,05 anos*.
        ])
      ]
    ],
    [
      #text(size: 9.8pt, weight: "bold", fill: c-navy, [B. Matriz $5 times 5$ no $W_2$ (de linha até coluna)])
      #v(2mm)
      #set table(
        stroke: (x, y) => if y == 0 { (bottom: 1.0pt + c-navy) } else { (bottom: 0.45pt + c-hair) },
        inset: (x: 6.5pt, y: 5.5pt),
        align: (left, right, right, right, right, right),
      )
      #text(size: 8.6pt, [
        #table(
          columns: (auto, auto, auto, auto, auto, auto),
          table.header([*de \\ até*], [*10*], [*20*], [*30*], [*40*], [*50*]),
          [*10*], text(fill: c-muted)[0], [11,73], [8,14], [9,49], [7,08],
          [*20*], [3,84], text(fill: c-muted)[0], [7,03], [8,30], [4,70],
          [*30*], [5,79], [12,55], text(fill: c-muted)[0], [8,30], [6,33],
          [*40*], [5,05], [12,32], [5,36], text(fill: c-muted)[0], [5,71],
          [*50*], [4,48], [12,23], [7,79], [8,26], text(fill: c-muted)[0],
        )
      ])
      #v(4mm)
      #card(accent: c-navy, inset-val: 3.0mm)[
        #text(size: 8.8pt, weight: "bold", fill: c-navy, [Caminhos mínimos validados até 100 ($W_2$)])
        #v(1.0mm)
        #text(size: 8.2pt, fill: c-slate, [
          • `10 → ... → 14144 → 100` (11 arestas, soma `10,47`)\
          • `20 → 6795 → 7737 → 11988 → 7094 → 14144 → 100` (6 ar., `8,48`)\
          • `30 → ... → 17695 → 14144 → 100` (11 arestas, soma `8,71`)\
          *(No $W_2$, `bellman_ford`, `floyd_warshall`, `johnson_heap` e `johnson_radix` coincidem no checksum `28,02`.)*
        ])
      ]
    ],
  )
]

// =============================================================================
// APÊNDICE A2 · CÓDIGO-CHAVE EM C++20
// =============================================================================
#page[
  #slide-head(
    "Apêndice · Q&A",
    "Trechos-chave em graph.hpp",
    sub: [Implementação em `C++20` sem dependências externas: detecção de ciclo $O(V)$, fila radix e relaxação vetorizável.],
  )
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 3.2mm,
    code-box(
      "has_cycle · stamps O(V) + tol.",
      ```cpp
      const auto first_stamp = stamp + 1;
      for (const auto start : changed) {
        const auto walk = ++stamp;
        for (auto v = start; v != no_vertex;
             v = next[v]) {
          if (stamps[v] == walk) return true;
          if (stamps[v] >= first_stamp) break;
          stamps[v] = walk;
        }
      }
      // Relaxação com margem IEEE-754:
      // tol = 8 * eps * V * max|w|
      if (cand < dist[prev] - tolerance) ...
      ```,
      accent: c-crimson,
    ),
    code-box(
      "RadixFrontier · 65 baldes",
      ```cpp
      void push(Vertex v, Weight d) {
        if (d == 0) d = 0; // -0.0 -> +0.0
        const auto key =
          std::bit_cast<std::uint64_t>(d);
        assert(key >= last_);
        if (key >= best_[v]) return;
        best_[v] = key;
        buckets_[bucket_of(key)]
          .push_back(Entry{key, v});
      }
      std::size_t bucket_of(uint64_t k) const {
        return std::bit_width(k ^ last_);
      }
      ```,
      accent: c-ochre,
    ),
    code-box(
      "relax_segment · branchless NEON",
      ```cpp
      for (std::size_t to = 0; to < w; ++to) {
        const auto cur  = row[to];
        const auto curp = row_parent[to];
        const auto thp  = through_parent[to];
        const auto cand = to_k + through[to];
        const auto ok   = cand < cur - tol;
        row[to]        = ok ? cand : cur;
        row_parent[to] = ok ? thp  : curp;
      }
      // Leituras antes dos ?: evitam desvios
      // condicionais -> auto-vetorizado NEON.
      ```,
      accent: c-navy,
    ),
  )
  #v(3mm)
  #card(accent: c-teal, inset-val: 2.8mm)[
    #text(size: 8.6pt, fill: c-slate, [
      *Garantias:* Em `has_cycle`, o lema $d[p] >= d["next"[p]] + w(p,"next"[p])$ somado à tolerância garante que todo ciclo em `next` tem soma negativa estrita. Em `RadixFrontier`, cada entrada só desce de balde quando `buckets_[0]` esvazia ($<= 64$ movimentos no pior caso). Em `relax_segment`, o compilador gera instruções vetoriais `NEON` sem intrínsecas.
    ])
  ]
]
