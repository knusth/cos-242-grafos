import random, sys
n, d, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])  # 5000 33 1
random.seed(seed); print(n)
for u in range(1, n + 1):
    for v in random.sample(range(1, n + 1), d):
        if v != u: print(u, v, round(random.uniform(0.5, 10), 2))
