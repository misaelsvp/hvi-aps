# Assembles the supplementary table: one row per census sector with its cluster, indicators and index.
# Output: data/sector_cluster_indicators.csv
# Requires: pandas

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
HVI_CSV = BASE / "data" / "hvi_by_sector.csv"
CLUSTER_CSV = BASE / "data" / "sector_cluster.csv"
OUT_CSV = BASE / "data" / "sector_cluster_indicators.csv"

SECTOR_KEY = "CD_SETOR"
SCORES = [
    "urban_infrastructure",
    "human_capital",
    "income_employment",
    "demographic_vulnerability",
]


def main():
    if not HVI_CSV.exists() or not CLUSTER_CSV.exists():
        return

    hvi = pd.read_csv(HVI_CSV, dtype={SECTOR_KEY: str})
    clusters = pd.read_csv(CLUSTER_CSV, dtype={SECTOR_KEY: str, "CD_UF": str})

    table = clusters[[SECTOR_KEY, "cluster"]].merge(hvi, on=SECTOR_KEY, how="left")

    # The 15-digit sector code carries the state in the first two digits and the
    # municipality in the first seven.
    table.insert(0, "estado", table[SECTOR_KEY].str[:2])
    table.insert(1, "municipio", table[SECTOR_KEY].str[:7])
    table = table.rename(columns={SECTOR_KEY: "setor_censitario", "hvi": "IVS"})

    indicators = [c for c in table.columns if c.startswith(("ui_", "hc_", "ie_", "dv_"))]
    columns = ["estado", "municipio", "cluster", "setor_censitario"] + indicators + SCORES + ["IVS", "population"]

    table[columns].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
