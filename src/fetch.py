"""Pull monthly files from OPM's Federal Workforce Data API.

Two datasets matter here. The employment file is a snapshot of everyone on the
payroll at the end of a month. The separations file is everyone who left during
that month, with a flag for the deferred resignation program.

Files land in data/raw as parquet. Already-downloaded months are skipped so
this is safe to rerun.
"""

import argparse
import os
import sys

import requests

BASE = "https://data.opm.gov/api/v1/files"
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def list_files(dataset):
    """Return the current version of every monthly file for a dataset."""
    r = requests.get(f"{BASE}/{dataset}", params={"current": "true"}, timeout=60)
    r.raise_for_status()
    return r.json()


def month_key(f):
    return f["year"] + f["month"]


def download(dataset, f, out_path):
    url = f"{BASE}/{dataset}/{f['year']}/{f['month']}/{f['version']}/download"
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        tmp = out_path + ".part"
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        os.replace(tmp, out_path)


def fetch(dataset, start, end):
    os.makedirs(RAW_DIR, exist_ok=True)
    files = [f for f in list_files(dataset) if start <= month_key(f) <= end]
    files.sort(key=month_key)
    for f in files:
        out = os.path.join(RAW_DIR, f"{dataset}_{month_key(f)}.parquet")
        if os.path.exists(out):
            print(f"skip {os.path.basename(out)}")
            continue
        print(f"get  {os.path.basename(out)} (v{f['version']})", flush=True)
        download(dataset, f, out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="202501", help="first month, YYYYMM")
    p.add_argument("--end", default="202607", help="last month, YYYYMM")
    p.add_argument("--datasets", nargs="+", default=["separations", "employment"])
    args = p.parse_args()
    for ds in args.datasets:
        fetch(ds, args.start, args.end)


if __name__ == "__main__":
    sys.exit(main())
