# Builds queen contiguity neighbour lists per state from the census sector shapefile.
# Output: data/contiguity_by_uf.pkl
# Requires: geopandas, pandas

import pickle
from pathlib import Path

import geopandas as gpd

BASE = Path(__file__).resolve().parent.parent
SHAPEFILE = BASE / "data" / "shapefiles" / "brazil_census_sectors_2022.shp"
OUT_PKL = BASE / "data" / "contiguity_by_uf.pkl"

SECTOR_KEY = "CD_SETOR"
STATE_KEY = "CD_UF"


def neighbours(sectors):
    sectors = sectors.reset_index(drop=True)
    code_of = sectors[SECTOR_KEY].to_dict()
    adjacency = {code: set() for code in sectors[SECTOR_KEY]}

    # Queen contiguity: the polygons share at least one boundary point and no interior,
    # which is what "touches" returns for sectors meeting along an edge or at a vertex.
    pairs = gpd.sjoin(sectors[["geometry"]], sectors[["geometry"]], predicate="touches", how="inner")
    for left, right in zip(pairs.index, pairs["index_right"]):
        if left == right:
            continue
        adjacency[code_of[left]].add(code_of[right])

    return {code: sorted(found) for code, found in adjacency.items()}


def main():
    if not SHAPEFILE.exists():
        return

    sectors = gpd.read_file(SHAPEFILE)
    sectors = sectors[[SECTOR_KEY, STATE_KEY, "geometry"]].copy()
    sectors[SECTOR_KEY] = sectors[SECTOR_KEY].astype(str)
    sectors[STATE_KEY] = sectors[STATE_KEY].astype(str)

    contiguity = {}
    for state, group in sectors.groupby(STATE_KEY, sort=True):
        contiguity[state] = neighbours(group)

    with OUT_PKL.open("wb") as f:
        pickle.dump(contiguity, f, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    main()
