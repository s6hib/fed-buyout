"""Turn the raw OPM files into a handful of small summary tables.

Everything here is a groupby. The interesting part is what gets compared to
what: buyout leavers are always set against the January 2025 workforce, which
is the last snapshot before the program was announced.

Outputs go to output/ as csv so the chart script and the readme can use them
without touching the raw parquet again.
"""

import glob
import os

import pandas as pd

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "output")

BASELINE = "202501"  # last snapshot before the deferred resignation offer
LATEST = "202607"

# columns we actually use, so the big employment files load faster
EMP_COLS = [
    "agency", "age_bracket", "length_of_service_years", "occupational_category",
    "stem_occupation", "annualized_adjusted_basic_pay", "supervisory_status",
    "duty_station_state",
]
SEP_COLS = EMP_COLS + ["separation_category", "drp_indicator",
                       "personnel_action_effective_date_yyyymm"]

AGE_ORDER = ["LESS THAN 20", "20-24", "25-29", "30-34", "35-39", "40-44",
             "45-49", "50-54", "55-59", "60-64", "65 OR MORE"]

SERVICE_BINS = [-1, 2, 5, 10, 15, 20, 30, 100]
SERVICE_LABELS = ["0-2", "3-5", "6-10", "11-15", "16-20", "21-30", "30+"]

PAY_BINS = [0, 50_000, 75_000, 100_000, 125_000, 150_000, 10_000_000]
PAY_LABELS = ["<50k", "50-75k", "75-100k", "100-125k", "125-150k", "150k+"]


def month_of(path):
    return os.path.basename(path).split("_")[1].split(".")[0]


def load_employment(month, cols=EMP_COLS):
    return pd.read_parquet(os.path.join(RAW, f"employment_{month}.parquet"), columns=cols)


def load_separations():
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW, "separations_*.parquet"))):
        df = pd.read_parquet(path, columns=SEP_COLS)
        df["file_month"] = month_of(path)
        frames.append(df)
    sep = pd.concat(frames, ignore_index=True)
    sep["drp"] = sep["drp_indicator"].eq("Y")
    return sep


def service_bucket(years):
    return pd.cut(years, bins=SERVICE_BINS, labels=SERVICE_LABELS)


def pay_band(pay):
    return pd.cut(pay, bins=PAY_BINS, labels=PAY_LABELS)


def headcount_by_month():
    """Total on payroll at the end of each month, from the snapshot files."""
    rows = []
    for path in sorted(glob.glob(os.path.join(RAW, "employment_*.parquet"))):
        n = len(pd.read_parquet(path, columns=["agency"]))
        rows.append({"month": month_of(path), "headcount": n})
    return pd.DataFrame(rows)


def agency_change(base, latest):
    """Headcount by agency at baseline vs latest, with the percent change."""
    b = base["agency"].value_counts().rename("baseline")
    l = latest["agency"].value_counts().rename("latest")
    df = pd.concat([b, l], axis=1).fillna(0).astype(int)
    df["change"] = df["latest"] - df["baseline"]
    df["pct_change"] = (df["change"] / df["baseline"] * 100).round(1)
    return df.reset_index().rename(columns={"index": "agency"}).sort_values("pct_change")


def separations_by_month(sep):
    """Leavers per month, split into buyout and everything else."""
    g = sep.groupby(["file_month", "drp"]).size().unstack(fill_value=0)
    g.columns = ["other", "buyout"]
    g["total"] = g["other"] + g["buyout"]
    return g.reset_index().rename(columns={"file_month": "month"})


def buyout_by_agency(sep, base):
    """Buyout leavers per agency as a share of that agency's Jan 2025 headcount."""
    took = sep[sep["drp"]]["agency"].value_counts().rename("buyout")
    size = base["agency"].value_counts().rename("baseline")
    df = pd.concat([size, took], axis=1).fillna(0).astype(int)
    df["pct_of_baseline"] = (df["buyout"] / df["baseline"] * 100).round(1)
    return df.reset_index().rename(columns={"index": "agency"}).sort_values("pct_of_baseline", ascending=False)


def share_table(sep, base, col, order=None):
    """Compare how a column is distributed among buyout leavers vs the baseline workforce.

    Returns one row per category with each group's share, so the two can sit
    side by side in a chart. A category that is over-represented among leavers
    has a ratio above 1.
    """
    took = sep[sep["drp"]][col].value_counts(normalize=True).rename("buyout_share")
    all_ = base[col].value_counts(normalize=True).rename("workforce_share")
    df = pd.concat([all_, took], axis=1).fillna(0)
    if order is not None:
        df = df.reindex([o for o in order if o in df.index])
    df["ratio"] = (df["buyout_share"] / df["workforce_share"]).round(2)
    df[["buyout_share", "workforce_share"]] = (df[["buyout_share", "workforce_share"]] * 100).round(2)
    return df.reset_index().rename(columns={"index": col})


def tenure_lost(sep):
    """How many years of service walked out under the buyout, and the typical leaver."""
    took = sep[sep["drp"]]
    yrs = took["length_of_service_years"].dropna()
    return pd.DataFrame([{
        "buyout_leavers": len(took),
        "total_service_years": int(yrs.sum()),
        "median_service_years": float(yrs.median()),
        "mean_service_years": round(float(yrs.mean()), 1),
        "median_pay": float(took["annualized_adjusted_basic_pay"].median()),
        "share_supervisors_pct": round(float(took["supervisory_status"].str.contains("SUPERVISOR|MANAGER", na=False).mean() * 100), 1),
    }])


def main():
    os.makedirs(OUT, exist_ok=True)
    base = load_employment(BASELINE)
    latest = load_employment(LATEST)
    sep = load_separations()

    base["service_bucket"] = service_bucket(base["length_of_service_years"])
    sep["service_bucket"] = service_bucket(sep["length_of_service_years"])
    base["pay_band"] = pay_band(base["annualized_adjusted_basic_pay"])
    sep["pay_band"] = pay_band(sep["annualized_adjusted_basic_pay"])

    tables = {
        "headcount_by_month": headcount_by_month(),
        "agency_change": agency_change(base, latest),
        "separations_by_month": separations_by_month(sep),
        "buyout_by_agency": buyout_by_agency(sep, base),
        "buyout_by_age": share_table(sep, base, "age_bracket", AGE_ORDER),
        "buyout_by_service": share_table(sep, base, "service_bucket", SERVICE_LABELS),
        "buyout_by_occupation": share_table(sep, base, "occupational_category"),
        "buyout_by_stem": share_table(sep, base, "stem_occupation"),
        "buyout_by_pay": share_table(sep, base, "pay_band", PAY_LABELS),
        "tenure_lost": tenure_lost(sep),
    }
    for name, df in tables.items():
        df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
        print(f"wrote {name} ({len(df)} rows)")



if __name__ == "__main__":
    main()
