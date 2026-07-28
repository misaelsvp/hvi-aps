# Aggregates census sectors into contiguous planning units that reach the ESF population reference.
# Output: data/sector_cluster.csv
# Requires: pandas

import heapq
import pickle
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
HVI_CSV = BASE / "data" / "hvi_by_sector.csv"
CONTIGUITY_PKL = BASE / "data" / "contiguity_by_municipality.pkl"
OUT_CSV = BASE / "data" / "sector_cluster.csv"

SECTOR_KEY = "CD_SETOR"
ATTRIBUTES = [
    "hvi",
    "urban_infrastructure",
    "human_capital",
    "income_employment",
    "demographic_vulnerability",
]
THRESHOLD = 3000


def ward_cost(a, b):
    weight = a["size"] * b["size"] / (a["size"] + b["size"])
    return weight * sum((x - y) ** 2 for x, y in zip(a["mean"], b["mean"]))


def union(a, b):
    size = a["size"] + b["size"]
    return {
        "members": a["members"] + b["members"],
        "population": a["population"] + b["population"],
        "size": size,
        "mean": tuple((a["size"] * x + b["size"] * y) / size for x, y in zip(a["mean"], b["mean"])),
        "neighbours": a["neighbours"] | b["neighbours"],
    }


def regionalize(sectors, adjacency, threshold):
    codes = list(sectors.index)
    position = {code: i for i, code in enumerate(codes)}

    regions = {}
    for code, i in position.items():
        row = sectors.loc[code]
        regions[i] = {
            "members": [code],
            "population": float(row["population"]),
            "size": 1,
            "mean": tuple(float(row[a]) for a in ATTRIBUTES),
            "neighbours": set(),
        }

    for code, i in position.items():
        for other in adjacency.get(code, ()):
            j = position.get(other)
            if j is not None and j != i:
                regions[i]["neighbours"].add(j)
                regions[j]["neighbours"].add(i)

    alive = set(regions)
    short = sum(1 for i in alive if regions[i]["population"] < threshold)

    heap = []
    for i in alive:
        for j in regions[i]["neighbours"]:
            if i < j:
                heapq.heappush(heap, (ward_cost(regions[i], regions[j]), i, j))

    following = len(regions)
    while heap and short:
        _, i, j = heapq.heappop(heap)
        if i not in alive or j not in alive:
            continue
        # A pair is only eligible while at least one of its regions is still below the threshold,
        # which keeps regions that already qualify from swallowing their neighbours.
        if regions[i]["population"] >= threshold and regions[j]["population"] >= threshold:
            continue

        merged = union(regions[i], regions[j])
        merged["neighbours"] -= {i, j}

        short -= (regions[i]["population"] < threshold) + (regions[j]["population"] < threshold)
        if merged["population"] < threshold:
            short += 1

        k = following
        following += 1
        regions[k] = merged
        alive.difference_update({i, j})
        alive.add(k)

        for n in merged["neighbours"]:
            if n not in alive:
                continue
            regions[n]["neighbours"].difference_update({i, j})
            regions[n]["neighbours"].add(k)
            heapq.heappush(heap, (ward_cost(merged, regions[n]), min(k, n), max(k, n)))

    return [regions[i]["members"] for i in sorted(alive)]


def main():
    if not HVI_CSV.exists() or not CONTIGUITY_PKL.exists():
        return

    hvi = pd.read_csv(HVI_CSV, dtype={SECTOR_KEY: str}).set_index(SECTOR_KEY)
    with CONTIGUITY_PKL.open("rb") as f:
        contiguity = pickle.load(f)

    rows = []
    for municipality, adjacency in contiguity.items():
        known = [code for code in adjacency if code in hvi.index]
        sectors = hvi.loc[known].dropna(subset=ATTRIBUTES + ["population"])
        if sectors.empty:
            continue
        for cluster, members in enumerate(regionalize(sectors, adjacency, THRESHOLD), start=1):
            rows.extend((code, municipality, cluster) for code in members)

    frame = pd.DataFrame(rows, columns=[SECTOR_KEY, "CD_MUN", "cluster"])
    frame.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
