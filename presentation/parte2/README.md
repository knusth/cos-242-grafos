# Apresentação da Parte 2

```sh
python3 -I presentation/parte2/build.py            # gera index.html e apresentacao.pdf
python3 -I presentation/parte2/build.py --sem-pdf  # só index.html
```

O PDF é impresso pelo Google Chrome em modo headless. Os números vêm de `report/parte2/data.json`,
`report/parte2/contagens.json`, `bench/results/parte2/caminhos_W_*.txt` e `pesos_W_3.json`/`pesos_W_7.json`.
O build não lê `data/`. Os dois `pesos_*.json` saem de `pesos_w.py`, que lê o arquivo do grafo uma vez
(`python3 -I pesos_w.py ../../report/parte2/data.json ../../data/grafo_W_7.txt W_7 pesos_W_7.json`, cerca de 40 s no W₇).
A linha de código mostrada é conferida contra `include/cos/graph.hpp` e leva o número real da linha:
se o código mudar, o build para com erro.

## Apresentar

- **PDF**: `apresentacao.pdf` em tela cheia, uma página por slide (16:9).
- **Navegador**: abra `index.html`.
  - Avançar: setas, espaço ou clique na tela.
  - Ir para o primeiro ou o último slide: Home e End.
  - `index.html#9` abre direto no slide 9.

A tela e o PDF mostram o mesmo conteúdo: não há animação, e todo gráfico é SVG estático.
São 12 slides (cerca de 7min30), sem apêndice.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `build.py` | slides, figuras e verificação do código |
| `pesos_w.py` | peso de cada aresta dos caminhos e peso médio de um grafo W |
| `../comum/estilo.css` | layout de seminário no estilo Metropolis (slide de 1280 × 720 px) |
| `../comum/fonts/` | Fira Sans (texto) e Inconsolata (código) |
| `ROTEIRO.md` | fala por slide, ganchos para improviso, perguntas prováveis, tempo |
| `index.html`, `apresentacao.pdf` | gerados |
