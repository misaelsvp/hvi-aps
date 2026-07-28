# Groups census sectors into contiguous clusters that stay within the ESF population reference.
# Output: data/sector_cluster.csv
# Requires: pandas

import pickle
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
HVI_CSV = BASE / "data" / "hvi_by_sector.csv"
CONTIGUITY_PKL = BASE / "data" / "contiguity_by_uf.pkl"
OUT_CSV = BASE / "data" / "sector_cluster.csv"

SECTOR_KEY = "CD_SETOR"
MAX_POP = 3000
SMALL_CLUSTER = 0.5 * MAX_POP


class UnionFind:
    def __init__(self, populations):
        n = len(populations)
        self.parent = list(range(n))
        self.rank = [0] * n
        self.population = list(populations)

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y, max_pop):
        a, b = self.find(x), self.find(y)
        if a == b:
            return False
        total = self.population[a] + self.population[b]
        if total > max_pop:
            return False
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        self.population[a] = total
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1
        return True


def group_state(sectors, adjacency):
    codes = list(sectors.index)
    position = {code: i for i, code in enumerate(codes)}
    hvi = sectors["hvi"].tolist()
    populations = sectors["population"].tolist()

    groups = UnionFind(populations)

    # A sector that already holds more people than one team can take stays on its own,
    # since any merge would breach the reference.
    isolated = {i for i, people in enumerate(populations) if people > MAX_POP}

    edges = []
    for code, i in position.items():
        if i in isolated:
            continue
        for neighbour in adjacency.get(code, ()):
            j = position.get(neighbour)
            if j is None or j <= i or j in isolated:
                continue
            edges.append((abs(hvi[i] - hvi[j]), i, j))

    # Closest pair in vulnerability first, so the most similar sectors merge while there is room.
    edges.sort()
    for _, i, j in edges:
        groups.union(i, j, MAX_POP)

    # Clusters that ended up well under the reference get one more attempt with a neighbour.
    for code, i in position.items():
        if i in isolated or groups.population[groups.find(i)] >= SMALL_CLUSTER:
            continue
        for neighbour in adjacency.get(code, ()):
            j = position.get(neighbour)
            if j is None or j in isolated:
                continue
            if groups.union(i, j, MAX_POP):
                break

    return {code: groups.find(i) for code, i in position.items()}


def main():
    if not HVI_CSV.exists() or not CONTIGUITY_PKL.exists():
        return

    hvi = pd.read_csv(HVI_CSV, dtype={SECTOR_KEY: str}).set_index(SECTOR_KEY)
    with CONTIGUITY_PKL.open("rb") as f:
        contiguity = pickle.load(f)

    rows = []
    for state in sorted(contiguity):
        adjacency = contiguity[state]
        known = [code for code in adjacency if code in hvi.index]
        sectors = hvi.loc[known].dropna(subset=["hvi", "population"])
        if sectors.empty:
            continue

        numbering = {}
        for code, root in group_state(sectors, adjacency).items():
            if root not in numbering:
                numbering[root] = len(numbering) + 1
            rows.append((code, state, numbering[root]))

    frame = pd.DataFrame(rows, columns=[SECTOR_KEY, "CD_UF", "cluster"])
    frame.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
