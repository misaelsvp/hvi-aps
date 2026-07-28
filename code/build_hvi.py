# Builds the Health Vulnerability Index by census sector from the 2022 Census aggregates.
# Output: data/hvi_by_sector.csv
# Requires: pandas

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
AGGREGATES = BASE / "data" / "census_2022_sector_aggregates.csv"
OUT_CSV = BASE / "data" / "hvi_by_sector.csv"

SECTOR_KEY = "CD_SETOR"

WATER = ["V00112", "V00113", "V00114", "V00115", "V00116", "V00117", "V00118"]
SEWAGE = ["V00311", "V00312", "V00313", "V00314", "V00315", "V00316"]
GARBAGE = ["V00399", "V00400", "V00401", "V00402"]
CROWDED = ["V00023", "V00024", "V00025", "V00026"]
SUBSTANDARD = ["V00050", "V00052", "V00053", "V00055", "V00056", "V00057"]
ELDERLY = ["V00654", "V00655", "V00656"]
DEPENDENTS = ["V01031", "V01032", "V01033", "V01040", "V01041"]
WORKING_AGE = ["V01034", "V01035", "V01036", "V01037", "V01038", "V01039"]
DEATHS_30_69 = ["V01234", "V01235", "V01236", "V01237", "V01245", "V01246", "V01247", "V01248"]
ADULTS_30_69 = ["V01037", "V01038", "V01039", "V01040"]

DIMENSIONS = {
    "urban_infrastructure": [
        "ui_water",
        "ui_sewage",
        "ui_garbage",
        "ui_bathroom",
        "ui_crowding",
    ],
    "human_capital": [
        "hc_illiteracy_15",
        "hc_illiteracy_15_29",
        "hc_female_head",
        "hc_illiterate_head",
        "hc_illiterate_female_head",
    ],
    "income_employment": [
        "ie_head_income",
        "ie_adolescent_head",
        "ie_substandard_housing",
    ],
    "demographic_vulnerability": [
        "dv_elderly",
        "dv_children",
        "dv_elderly_head",
        "dv_dependency",
        "dv_premature_mortality",
    ],
}


def ratio(numerator, denominator):
    out = numerator / denominator
    return out.where(denominator > 0)


def indicators(df):
    ind = pd.DataFrame(index=df.index)
    households = df["V00001"]
    residents = df["V01006"]

    ind["ui_water"] = ratio(df[WATER].sum(axis=1), households)
    ind["ui_sewage"] = ratio(df[SEWAGE].sum(axis=1), households)
    ind["ui_garbage"] = ratio(df[GARBAGE].sum(axis=1), households)
    ind["ui_bathroom"] = ratio(df["V00495"], households)
    ind["ui_crowding"] = ratio(df[CROWDED].sum(axis=1), households)

    ind["hc_illiteracy_15"] = ratio(df["V00901"], df["V00900"] + df["V00901"])
    ind["hc_illiteracy_15_29"] = ratio(df["V00853"], df["V00852"] + df["V00853"])
    ind["hc_female_head"] = ratio(df["V01204"], households)
    ind["hc_illiterate_head"] = ratio(df["V00985"], df["V00984"] + df["V00985"])
    ind["hc_illiterate_female_head"] = ratio(df["V00989"], df["V00988"] + df["V00989"])

    # Income enters inverted, so that a lower head-of-household income means a higher rank.
    ind["ie_head_income"] = -df["V06006"]
    ind["ie_adolescent_head"] = ratio(df["V01064"], households)
    ind["ie_substandard_housing"] = ratio(df[SUBSTANDARD].sum(axis=1), households + df["V00002"])

    ind["dv_elderly"] = ratio(df[ELDERLY].sum(axis=1), residents)
    ind["dv_children"] = ratio(df["V01031"], residents)
    ind["dv_elderly_head"] = ratio(df["V01068"], households)
    ind["dv_dependency"] = ratio(df[DEPENDENTS].sum(axis=1), df[WORKING_AGE].sum(axis=1))
    ind["dv_premature_mortality"] = ratio(df[DEATHS_30_69].sum(axis=1), df[ADULTS_30_69].sum(axis=1))
    return ind


def main():
    if not AGGREGATES.exists():
        return

    df = pd.read_csv(AGGREGATES, dtype={SECTOR_KEY: str}).set_index(SECTOR_KEY)

    ind = indicators(df)
    ranked = ind.rank(pct=True)

    scores = pd.DataFrame(index=ind.index)
    for dimension, columns in DIMENSIONS.items():
        scores[dimension] = ranked[columns].mean(axis=1)
    scores["hvi"] = scores[list(DIMENSIONS)].mean(axis=1)
    scores["population"] = df["V01006"]

    ind.join(scores).to_csv(OUT_CSV, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
