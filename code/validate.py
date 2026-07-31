# Computes the validation statistics reported for the index and for the resulting territories.
# Output: data/validation_report.txt
# Requires: pandas, geopandas, shapely

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
HVI_CSV = BASE / "data" / "hvi_by_sector.csv"
CLUSTER_CSV = BASE / "data" / "sector_cluster.csv"
SHAPEFILE = BASE / "data" / "shapefiles" / "brazil_census_sectors_2022.shp"
IPEA_CSV = BASE / "data" / "ipea_ivs_by_municipality.csv"
OUT_TXT = BASE / "data" / "validation_report.txt"

SECTOR_KEY = "CD_SETOR"
DIMENSIONS = [
    "urban_infrastructure",
    "human_capital",
    "income_employment",
    "demographic_vulnerability",
]
PREFIX = {
    "urban_infrastructure": "ui_",
    "human_capital": "hc_",
    "income_employment": "ie_",
    "demographic_vulnerability": "dv_",
}
THRESHOLD = 3000
PERMUTATIONS = 999
MORAN_CASE = "3106200"   # Belo Horizonte, the municipal case study


def cronbach_alpha(frame):
    # Equation (4). Components are the columns; q is how many there are.
    frame = frame.dropna()
    q = frame.shape[1]
    if q < 2 or len(frame) < 2:
        return float("nan")
    total = frame.sum(axis=1).var(ddof=1)
    if total == 0:
        return float("nan")
    return (q / (q - 1)) * (1 - frame.var(ddof=1).sum() / total)


def aggregate_to_municipality(tracts):
    # Equation (5). Population-weighted mean, so that a 50-resident tract does not
    # count as much as a 5,000-resident one.
    weighted = tracts["hvi"] * tracts["population"]
    grouped = pd.DataFrame({"num": weighted, "den": tracts["population"], "mun": tracts["CD_MUN"]})
    totals = grouped.groupby("mun").sum()
    return (totals["num"] / totals["den"]).rename("hvi_municipality")


def spearman(a, b):
    # Equation (6). Pearson on the ranks, which is what the shortcut with the sum of
    # squared rank differences reduces to when there are no ties.
    joined = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(joined) < 3:
        return float("nan"), 0
    return joined.iloc[:, 0].corr(joined.iloc[:, 1], method="spearman"), len(joined)


def queen_weights(sectors):
    sectors = sectors.reset_index(drop=True)
    try:
        # Queen contiguity from shared vertices. Preferred because the published meshes carry
        # slivers: adjacent tracts can overlap slightly, which a "touches" predicate drops, or
        # meet along a shared border that "intersects" would count more than once.
        from libpysal.weights import Queen

        weights = Queen.from_dataframe(sectors, use_index=False)
        return [list(weights.neighbors[i]) for i in range(len(sectors))]
    except ImportError:
        import geopandas as gpd

        pairs = gpd.sjoin(sectors[["geometry"]], sectors[["geometry"]],
                          predicate="intersects", how="inner")
        neighbours = [[] for _ in range(len(sectors))]
        for left, right in zip(pairs.index, pairs["index_right"]):
            if left != right:
                neighbours[left].append(right)
        return neighbours


def morans_i(values, neighbours, permutations=PERMUTATIONS, seed=0):
    # Equation (7) with row-standardised weights, so each tract is compared with the
    # mean of its neighbours and a tract with 12 neighbours does not outweigh one with 3.
    values = np.asarray(values, dtype=float)
    n = len(values)
    deviation = values - values.mean()
    denominator = (deviation ** 2).sum()
    if denominator == 0:
        return float("nan"), float("nan"), float("nan")

    def statistic(dev):
        numerator = 0.0
        weight_total = 0.0
        for i, near in enumerate(neighbours):
            if not near:
                continue
            weight = 1.0 / len(near)
            numerator += weight * dev[i] * dev[list(near)].sum()
            weight_total += 1.0
        if weight_total == 0:
            return float("nan")
        return (n / weight_total) * (numerator / denominator)

    observed = statistic(deviation)
    rng = np.random.default_rng(seed)
    extreme = 0
    for _ in range(permutations):
        if statistic(rng.permutation(deviation)) >= observed:
            extreme += 1
    pseudo_p = (1 + extreme) / (permutations + 1)
    return observed, -1.0 / (n - 1), pseudo_p


def eta_squared(values, labels):
    # Equation (8). Share of the tract-level variance preserved between planning units.
    frame = pd.DataFrame({"v": np.asarray(values, dtype=float), "k": np.asarray(labels)})
    total = ((frame["v"] - frame["v"].mean()) ** 2).sum()
    if total == 0:
        return float("nan")
    within = ((frame["v"] - frame.groupby("k")["v"].transform("mean")) ** 2).sum()
    return 1 - within / total


def population_balance(cluster_population):
    # Equation (9) and the share of units within the caseload reference.
    mean = cluster_population.mean()
    cv = cluster_population.std(ddof=1) / mean if mean else float("nan")
    return cv, (cluster_population <= THRESHOLD).mean()


def reduction(n_tracts, n_clusters):
    # Equation (10).
    return 1 - n_clusters / n_tracts


def load():
    if not HVI_CSV.exists() or not CLUSTER_CSV.exists():
        return None
    hvi = pd.read_csv(HVI_CSV, dtype={SECTOR_KEY: str}).set_index(SECTOR_KEY)
    clusters = pd.read_csv(CLUSTER_CSV, dtype={SECTOR_KEY: str, "CD_UF": str, "CD_MUN": str})
    merged = clusters.join(hvi, on=SECTOR_KEY, how="inner")
    return merged.dropna(subset=["hvi", "population"])


def report(tracts, lines):
    say = lines.append
    say("tracts with index and cluster: %d" % len(tracts))
    say("total residents: %d" % tracts["population"].sum())
    say("median residents per tract: %.0f" % tracts["population"].median())
    oversized = tracts["population"] > THRESHOLD
    say("tracts above the reference on their own: %d (%.4f%%), holding %.4f%% of the population"
        % (oversized.sum(), 100 * oversized.mean(),
           100 * tracts.loc[oversized, "population"].sum() / tracts["population"].sum()))

    say("")
    say("Equation (4), internal consistency")
    present = [d for d in DIMENSIONS if d in tracts.columns]
    if not present:
        # Earlier specifications of the index carried a different set of dimensions.
        # Fall back to whatever dimension columns the file actually holds.
        skip = {"population", "hvi", "cluster"}
        present = [c for c in tracts.columns
                   if c not in skip
                   and not any(c.startswith(p) for p in PREFIX.values())
                   and pd.api.types.is_numeric_dtype(tracts[c])]
    for dimension in present:
        indicators = [c for c in tracts.columns if c.startswith(PREFIX.get(dimension, "\0"))]
        if len(indicators) > 1:
            say("  alpha within %-28s = %.4f" % (dimension, cronbach_alpha(tracts[indicators])))
    if len(present) > 1:
        say("  alpha over the dimension scores  = %.4f" % cronbach_alpha(tracts[present]))
        for dropped in present:
            rest = [d for d in present if d != dropped]
            say("    without %-28s = %.4f" % (dropped, cronbach_alpha(tracts[rest])))

    say("")
    say("Equations (5) and (6), convergent validity")
    if IPEA_CSV.exists() and "CD_MUN" in tracts.columns:
        ours = aggregate_to_municipality(tracts)
        theirs = pd.read_csv(IPEA_CSV, dtype={"CD_MUN": str}).set_index("CD_MUN").iloc[:, 0]
        rho, matched = spearman(ours, theirs)
        say("  Spearman against the IPEA index = %.4f over %d municipalities" % (rho, matched))
    else:
        say("  skipped, %s not present" % IPEA_CSV.name)

    say("")
    say("Equation (7), spatial autocorrelation")
    if SHAPEFILE.exists() and "CD_MUN" in tracts.columns:
        import geopandas as gpd

        shape = gpd.read_file(SHAPEFILE, where="CD_MUN = '%s'" % MORAN_CASE)
        shape[SECTOR_KEY] = shape[SECTOR_KEY].astype(str)
        case = shape.merge(tracts.reset_index()[[SECTOR_KEY, "hvi"]], on=SECTOR_KEY, how="inner")
        case = case[case.geometry.notna() & ~case.geometry.is_empty]
        if len(case) > 2:
            observed, expected, pseudo_p = morans_i(case["hvi"].values, queen_weights(case))
            say("  municipality %s: n = %d" % (MORAN_CASE, len(case)))
            say("  I = %.4f, E[I] = %.6f, pseudo p = %.4f over %d permutations"
                % (observed, expected, pseudo_p, PERMUTATIONS))
    else:
        say("  skipped, shapefile not present")

    say("")
    say("Equations (8) to (10), quality of the resulting territories")
    key = ["CD_UF", "cluster"] if "CD_UF" in tracts.columns else ["cluster"]
    labels = tracts.groupby(key).ngroup()
    cluster_population = tracts.groupby(key)["population"].sum()
    cv, within = population_balance(cluster_population)
    say("  clusters: %d" % len(cluster_population))
    say("  eta squared = %.4f" % eta_squared(tracts["hvi"], labels))
    say("  CV = %.4f, units within the reference = %.2f%%" % (cv, 100 * within))
    say("  reduction = %.2f%%" % (100 * reduction(len(tracts), len(cluster_population))))

    rng = np.random.default_rng(0)
    sizes = cluster_population.index.map(tracts.groupby(key).size())
    shuffled = rng.permutation(np.repeat(np.arange(len(sizes)), sizes))
    say("  eta squared of a random partition with the same sizes = %.4f"
        % eta_squared(tracts["hvi"], shuffled))


def main():
    tracts = load()
    if tracts is None:
        print("missing inputs, run build_hvi.py and cluster_sectors.py first", file=sys.stderr)
        return

    lines = []
    report(tracts, lines)
    text = "\n".join(lines)
    OUT_TXT.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
