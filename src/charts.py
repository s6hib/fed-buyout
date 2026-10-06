"""Draw the charts from the csv tables in output/.

Kept deliberately plain: matplotlib defaults with a couple of tweaks so the
pngs read fine inside a readme at half width.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "output")

BLUE = "#2b5f9e"
ORANGE = "#d9742b"
GRAY = "#9a9a9a"


def load(name):
    return pd.read_csv(os.path.join(OUT, f"{name}.csv"))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"{name}.png"), dpi=150)
    plt.close(fig)


def month_label(m):
    m = str(m)
    return pd.Timestamp(int(m[:4]), int(m[4:]), 1).strftime("%b %Y")


def tidy(name):
    """Shorten the official agency names so they fit on a y axis."""
    name = name.title()
    for a, b in [("Department Of The ", ""), ("Department Of ", ""), ("Nat Aeronautics And Space Administration", "NASA"),
                 ("Housing And Urban Developm", "HUD"), ("Environmental Protection Agency", "EPA"),
                 ("General Services Administration", "GSA"), ("Small Business Administration", "SBA"),
                 ("Health And Human Services", "HHS"), ("Social Security Administration", "SSA"),
                 ("Federal Deposit Insurance Corporation", "FDIC"), ("Office Of Personnel Management", "OPM"),
                 ("Veterans Affairs", "VA"), ("Homeland Security", "DHS"), (" Of ", " of "), (" And ", " and "),
                 (" The ", " the ")]:
        name = name.replace(a, b)
    return name


def chart_headcount():
    df = load("headcount_by_month")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(range(len(df)), df["headcount"] / 1e6, color=BLUE, lw=2.5, marker="o", ms=4)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels([month_label(m) if i % 3 == 0 else "" for i, m in enumerate(df["month"])], rotation=0)
    ax.set_ylabel("federal civilian employees (millions)")
    ax.set_title("The federal workforce, month by month", loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    first, last = df.iloc[0], df.iloc[-1]
    ax.annotate(f"{first.headcount/1e6:.2f}M", (0, first.headcount / 1e6), xytext=(6, 8), textcoords="offset points")
    ax.annotate(f"{last.headcount/1e6:.2f}M", (len(df) - 1, last.headcount / 1e6), xytext=(-34, 8), textcoords="offset points")
    save(fig, "headcount_by_month")


def chart_agency_change(min_size=5000, n=15):
    df = load("agency_change")
    df = df[df["baseline"] >= min_size].sort_values("pct_change").head(n)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh([tidy(a) for a in df["agency"]], df["pct_change"], color=BLUE)
    ax.invert_yaxis()
    ax.set_xlabel("% change in headcount, Jan 2025 to Jul 2026")
    ax.set_title(f"Biggest cuts by agency (agencies with {min_size:,}+ staff)", loc="left", fontweight="bold")
    for i, v in enumerate(df["pct_change"]):
        ax.text(v - 0.4, i, f"{v:.0f}%", va="center", ha="right", fontsize=9)
    ax.set_xlim(df["pct_change"].min() * 1.12, 0)
    ax.grid(axis="x", alpha=0.3)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    save(fig, "agency_change")


def chart_separations_by_month():
    df = load("separations_by_month")
    x = range(len(df))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x, df["other"] / 1e3, color=GRAY, label="all other separations")
    ax.bar(x, df["buyout"] / 1e3, bottom=df["other"] / 1e3, color=ORANGE, label="deferred resignation")
    ax.set_xticks(list(x))
    ax.set_xticklabels([month_label(m) if i % 2 == 0 else "" for i, m in enumerate(df["month"])])
    ax.set_ylabel("people leaving (thousands)")
    ax.set_title("When the buyout hit", loc="left", fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    save(fig, "separations_by_month")


def chart_buyout_by_agency(min_size=5000, n=15):
    df = load("buyout_by_agency")
    df = df[df["baseline"] >= min_size].sort_values("pct_of_baseline", ascending=False).head(n)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh([tidy(a) for a in df["agency"]], df["pct_of_baseline"], color=ORANGE)
    ax.invert_yaxis()
    ax.set_xlabel("buyout leavers as % of Jan 2025 headcount")
    ax.set_title("Which agencies lost the most staff to the buyout", loc="left", fontweight="bold")
    for i, (v, n_) in enumerate(zip(df["pct_of_baseline"], df["buyout"])):
        ax.text(v + 0.2, i, f"{v:.1f}%  ({n_:,})", va="center", fontsize=9)
    ax.set_xlim(0, df["pct_of_baseline"].max() * 1.25)
    ax.grid(axis="x", alpha=0.3)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    save(fig, "buyout_by_agency")


def short_label(v):
    v = str(v)
    fixes = {"LESS THAN 20": "<20", "65 OR MORE": "65+", "ALL OTHER OCCUPATIONS": "Everything else",
             "STEM OCCUPATIONS": "STEM", "HEALTH OCCUPATIONS": "Health", "UNSPECIFIED": "Unspecified"}
    return fixes.get(v, v.title() if len(v) > 6 else v)


def chart_share(name, col, title, xlabel=None):
    """Side by side bars: share of buyout leavers vs share of the Jan 2025 workforce."""
    df = load(name)
    x = range(len(df))
    w = 0.4
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar([i - w / 2 for i in x], df["workforce_share"], w, color=GRAY, label="whole workforce, Jan 2025")
    ax.bar([i + w / 2 for i in x], df["buyout_share"], w, color=ORANGE, label="took the buyout")
    ax.set_xticks(list(x))
    ax.set_xticklabels([short_label(v) for v in df[col]], rotation=0)
    ax.set_ylabel("share of group (%)")
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    save(fig, name)


def main():
    chart_headcount()
    chart_agency_change()
    chart_separations_by_month()
    chart_buyout_by_agency()
    chart_share("buyout_by_age", "age_bracket", "Who took it: age", "age bracket")
    chart_share("buyout_by_service", "service_bucket", "Who took it: years of federal service", "years of service")
    chart_share("buyout_by_pay", "pay_band", "Who took it: salary", "annual basic pay")
    chart_share("buyout_by_stem", "stem_occupation", "Who took it: STEM, health, everyone else")
    print("charts written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
