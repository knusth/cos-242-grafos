# Relatório da Parte 3

Reconstruir, a partir da raiz do repositório (os resultados vêm de `bench/run_part3.sh`):

```sh
python3 -I bench/summarize_p3.py          # bench/results/parte3/* -> report/parte3/data.json
python3 -I report/parte3/tabelas.py       # data.json -> tabelas.tex e relax.txt
(cd report/parte3 && tectonic relatorio.tex)
```

- Resultados parciais funcionam: o que falta aparece como `---` no PDF.
- `tabelas.py` compara o W_2 com as distâncias de referência (Dijkstra independente) e imprime
  `DIVERGÊNCIA W_2: ...` em stderr se houver diferença.
- O texto de `relatorio.tex` usa números só via `\dado{chave}`; releia as frases
  qualitativas depois de atualizar os dados.
- `data.json` também alimenta a apresentação (esquema na docstring de `bench/summarize_p3.py`).
