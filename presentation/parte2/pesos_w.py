"""Pesos das arestas dos caminhos de um grafo W (lidos de data/grafo_<W>.txt) para a apresentação.
Uso: python3 -I pesos_w.py ../../report/parte2/data.json ../../data/grafo_W_3.txt W_3 pesos_W_3.json"""
import json, sys

path_json, arquivo, nome, out = sys.argv[1:5]
G = {g['name']: g for g in json.load(open(path_json))['graphs']}[nome]
pares = {}
for p in G['paths']:
    for a, b in zip(p['path'], p['path'][1:]):
        pares[(min(a, b), max(a, b))] = None
bins = [0] * 40
m, soma, leves = 0, 0.0, 0
with open(arquivo) as f:
    n = int(f.readline())
    for line in f:
        a, b, w = line.split()
        w = float(w)
        m += 1
        soma += w
        bins[min(int(w / 10 * 40), 39)] += 1
        a, b = int(a), int(b)
        k = (a, b) if a < b else (b, a)
        if k in pares and (pares[k] is None or w < pares[k]):
            pares[k] = w
res = {'nome': nome, 'n': n, 'm': m, 'media': soma / m, 'bins': bins,
       'caminhos': [{'target': p['target'], 'distance': p['distance'], 'path': p['path'],
                     'pesos': [pares[(min(a, b), max(a, b))] for a, b in zip(p['path'], p['path'][1:])]}
                    for p in G['paths']]}
mx = max(w for c in res['caminhos'] for w in c['pesos'])
res['max_caminho'] = mx
json.dump(res, open(out, 'w'), indent=1)
for c in res['caminhos']:
    print(c['target'], c['distance'], round(sum(c['pesos']), 4), len(c['pesos']))
print(nome, n, m, round(soma / m, 3), 'max no caminho', mx)
