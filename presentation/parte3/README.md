# Apresentação da Parte 3

Apresentação em 12 slides principais (8 minutos) + 2 slides de apêndice para Q&A (14 páginas em 16:9), produzida em **Typst** com figuras vetoriais (SVG) geradas a partir dos mesmos dados medidos do relatório.

## Reconstruir o PDF

Requer Python 3 e [Typst](https://typst.app/). A partir da raiz do repositório:

```sh
(cd presentation/parte3 && python3 generate_assets.py && typst compile slides.typ apresentacao.pdf)
```

`generate_assets.py` lê os resultados em `report/parte3/*.json`, `bench/results/parte3/*.txt` e constantes em `include/cos/graph.hpp` para gerar os 11 SVGs em `assets/`. Em seguida, `typst compile` compila `slides.typ` em `apresentacao.pdf`.

Se os dados de benchmark mudarem, rode primeiro `python3 -I bench/parte3/summarize_p3.py` (e, se aplicável, `report/parte3/tabelas.py`) antes de regerar os SVGs e recompilar os slides.

## Arquivos

| Arquivo | Função |
|---|---|
| `slides.typ` | Fonte Typst dos 12 slides principais + 2 apêndices (Q&A) |
| `generate_assets.py` | Gera os 11 diagramas e gráficos vetoriais em `assets/fig_*.svg` |
| `assets/fig_*.svg` | Figuras vetoriais incorporadas por `slides.typ` |
| `apresentacao.pdf` | PDF compilado pronto para apresentação em tela cheia (16:9) |
| `ROTEIRO.md` | Roteiro cronometrado por slide (8 min · ~120 palavras/min) e notas para Q&A |

## Estrutura dos slides

1. **Ato 1 — Problema e Bellman-Ford (Slides 1–4):** capa, escala dos grafos $W_1$–$W_5$ e limite de RAM (`12·V²`), lista de ativos + parada antecipada, detecção de ciclos negativos em $O(V)$ e tolerância IEEE-754.
2. **Ato 2 — Todos os pares e hardware (Slides 5–7):** comparação de tempos (BF vs. FW, $13\times$), decomposição de fatores ($211\times$ menos relaxações $\div$ $16\times$ mais caro por relaxação) e efeito da cache L2 em 10M vértices.
3. **Ato 3 — Algoritmo de Johnson (Slides 8–9):** potencial telescópico $h$, fila radix de 65 baldes (`std::bit_cast`) e benchmark $2{,}4\times$ sobre Bellman-Ford no $W_2$.
4. **Ato 4 — Paralelismo e síntese (Slides 10–12):** destinos independentes vs. blocos $64 \times 64$ com barreiras, escala em núcleos P/E e parede da L2, síntese e matriz de decisão.
5. **Apêndice (A1–A2):** tabela completa de distâncias até o vértice 100 e matriz $5 \times 5$ do $W_2$, além dos trechos-chave de `include/cos/graph.hpp`.
