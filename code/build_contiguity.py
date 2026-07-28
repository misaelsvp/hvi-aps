# Builds queen contiguity neighbour lists per municipality from the census sector shapefile.
# Output: data/contiguity_by_municipality.pkl
# Requires: geopandas, pandas

import pickle
from pathlib import Path

import geopandas as gpd

BASE = Path(__file__).resolve().parent.parent
SHAPEFILE = BASE / "data" / "shapefiles" / "brazil_census_sectors_2022.shp"
OUT_PKL = BASE / "data" / "contiguity_by_municipality.pkl"

SECTOR_KEY = "CD_SETOR"
MUNICIPALITY_KEY = "CD_MUN"


def neighbours(sectors):
    sectors = sectors.reset_index(drop=True)
    code_of = sectors[SECTOR_KEY].to_dict()
    adjacency = {code: set() for code in sectors[SECTOR_KEY]}

    # Two sectors are queen neighbours when their polygons share at least one boundary point,
    # which is what "touches" returns for polygons that meet along an edge or at a vertex.
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
    sectors = sectors[[SECTOR_KEY, MUNICIPALITY_KEY, "geometry"]].copy()
    sectors[SECTOR_KEY] = sectors[SECTOR_KEY].astype(str)
    sectors[MUNICIPALITY_KEY] = sectors[MUNICIPALITY_KEY].astype(str)

    contiguity = {}
    for municipality, group in sectors.groupby(MUNICIPALITY_KEY, sort=True):
        contiguity[municipality] = neighbours(group)

    with OUT_PKL.open("wb") as f:
        pickle.dump(contiguity, f, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    main()
