# Builds setor -> cluster table from shapefile + state_map GeoJSON.
# Output: data/state_maps/setor_cluster_por_uf.csv
# Requires: geopandas, pandas

import json
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

UF_SIGLA_TO_CD = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35",
    "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}

BASE = Path(__file__).resolve().parent.parent
SHAPEFILE = BASE / "data" / "shapefiles" / "brazil_census_sectors_2022.shp"
STATE_MAPS_DIR = BASE / "data" / "state_maps"
OUT_CSV = BASE / "data" / "sector_cluster_by_uf.csv"


def extract_geojson_blobs(html_path):
    text = html_path.read_text(encoding="utf-8", errors="replace")
    blobs = []
    i = 0
    while True:
        idx = text.find("_add(", i)
        if idx == -1:
            break
        start = idx + len("_add(")
        pos = start
        while pos < len(text) and text[pos] in " \t\n\r":
            pos += 1
        if pos >= len(text) or text[pos] != "{":
            i = start
            continue
        depth = 0
        in_string = False
        escape = False
        quote = None
        for j in range(pos, len(text)):
            c = text[j]
            if escape:
                escape = False
                continue
            if c == "\\" and in_string:
                escape = True
                continue
            if not in_string:
                if c in "\"'":
                    in_string = True
                    quote = c
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        blobs.append(text[pos : j + 1])
                        break
            else:
                if c == quote:
                    in_string = False
            if depth == 0:
                break
        i = start + 1
    return blobs


def parse_features_from_blobs(blobs):
    features = []
    for s in blobs:
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            continue
        for f in data.get("features", []):
            geom = f.get("geometry")
            props = f.get("properties") or {}
            cluster = props.get("cluster")
            if geom is not None and cluster is not None:
                features.append({"geometry": shape(geom), "cluster": int(float(cluster))})
    return features


def cluster_gdf_for_state(html_path):
    blobs = extract_geojson_blobs(html_path)
    features = parse_features_from_blobs(blobs)
    if not features:
        return gpd.GeoDataFrame()
    return gpd.GeoDataFrame(
        [{"geometry": f["geometry"], "cluster": f["cluster"]} for f in features],
        crs="EPSG:4674",
    )


def run_state(sigla, cd_uf):
    html_path = STATE_MAPS_DIR / f"state_map_{sigla}.html"
    if not html_path.exists():
        return pd.DataFrame()

    clusters_gdf = cluster_gdf_for_state(html_path)
    if clusters_gdf.empty:
        return pd.DataFrame()

    minx, miny, maxx, maxy = clusters_gdf.total_bounds
    bbox = (minx - 0.1, miny - 0.1, maxx + 0.1, maxy + 0.1)

    setores = gpd.read_file(SHAPEFILE, bbox=bbox)
    setores = setores[setores["CD_UF"].astype(str) == str(cd_uf)]
    if setores.empty:
        return pd.DataFrame()

    setores = setores.copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        setores["centroid"] = setores.geometry.centroid
    setores_pt = setores.set_geometry("centroid")[["CD_SETOR", "CD_UF", "centroid"]]

    join = gpd.sjoin(
        setores_pt,
        clusters_gdf[["geometry", "cluster"]],
        how="left",
        predicate="within",
    )
    join = join.drop_duplicates(subset=["CD_SETOR"], keep="first")
    result = join[["CD_SETOR", "CD_UF", "cluster"]].copy()
    result["SIGLA_UF"] = sigla

    missing = result["cluster"].isna()
    if missing.any():
        setores_sem = setores[setores["CD_SETOR"].isin(result.loc[missing, "CD_SETOR"])].copy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            for idx, row in setores_sem.iterrows():
                inter = clusters_gdf.copy()
                inter["area_inter"] = inter.geometry.intersection(row.geometry).area
                inter = inter.sort_values("area_inter", ascending=False)
                if inter.iloc[0]["area_inter"] > 0:
                    result.loc[result["CD_SETOR"] == row["CD_SETOR"], "cluster"] = inter.iloc[0]["cluster"]

    result["cluster"] = result["cluster"].astype("Int64")
    return result


def main():
    if not SHAPEFILE.exists():
        return
    STATE_MAPS_DIR.mkdir(parents=True, exist_ok=True)

    only_states = []
    uf_items = [(s, c) for s, c in UF_SIGLA_TO_CD.items() if not only_states or s in only_states]
    all_dfs = []
    for sigla, cd_uf in uf_items:
        df = run_state(sigla, cd_uf)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        return

    out = pd.concat(all_dfs, ignore_index=True)
    out = out[["CD_SETOR", "CD_UF", "SIGLA_UF", "cluster"]]
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
