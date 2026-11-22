# Apresentação da Parte 3

```sh
python3 -I presentation/parte3/build.py            # gera index.html e apresentacao.pdf
python3 -I presentation/parte3/build.py --sem-pdf  # só index.html
python3 -I presentation/parte3/build.py --dados OUTRO.json   # outro data.json (teste)
```

O PDF é impresso pelo Google Chrome em modo headless. Todo número de resultado vem de
`report/parte3/data.json` (gerado por `bench/summarize_p3.py` a partir de `bench/results/parte3/`).
Rode o resumo e o build de novo quando o benchmark terminar:

```sh
python3 -I bench/summarize_p3.py
python3 -I presentation/parte3/build.py
```

Valor ainda ausente aparece como "—", e a linha do grafo leva a marca "em execução". O build imprime a lista
de campos pendentes. O trecho de código do slide 4 é conferido contra `include/cos/graph.hpp` (com o número
real das linhas); se o código mudar, o build para com erro.

## Apresentar

- **PDF**: `apresentacao.pdf` em tela cheia, uma página por slide (16:9).
- **Navegador**: abra `index.html`. Setas, espaço ou clique avançam; Home e End vão ao primeiro e ao último;
  `index.html#10` abre direto no slide 10.

Tela e PDF mostram o mesmo conteúdo: sem animação, gráficos em SVG estático.
São 11 slides, cerca de 7min20. Veja `ROTEIRO.md` (gerado de `ROTEIRO.modelo.md`).

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `build.py` | slides, figuras e verificação do código |
| `ROTEIRO.modelo.md` | fala por slide, tempos, perguntas prováveis; os números são marcadores `{{...}}`, e o build gera `ROTEIRO.md` (não edite) com os mesmos valores dos slides |
| `../comum/estilo.css`, `../comum/fonts/` | estilo (1280 × 720 px) e fontes Fira Sans e Inconsolata |
| `index.html`, `apresentacao.pdf` | gerados |

## Como ler os valores estimados

- Floyd-Warshall do W₃ em diante: média medida no W₂ × (V/V₂)³ (a matriz não cabe na RAM).
- Todos-pares por Bellman-Ford do W₃ em diante: destinos amostrados em 1 thread e extrapolados para V.
  No gráfico do slide 10 o tempo é dividido por 11 (escala linear), para comparar com o Floyd-Warshall em 11 threads.
- W₁: os três tempos são de detecção do ciclo negativo.
- A tabela 5×5 do W₃ ao W₅ vem do Bellman-Ford (uma execução por destino).
