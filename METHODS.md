# Methods and caveats

## Data

Everything comes from OPM's Federal Workforce Data site (data.opm.gov), which
replaced FedScope in January 2026. Two record-level datasets are used:

- Employment: a snapshot of every federal civilian employee on the last day of
  each month. One row per person.
- Separations: every personnel action that took someone off the rolls that
  month, with a `drp_indicator` column that marks the deferred resignation
  program.

`src/fetch.py` pulls both for January 2025 through July 2026 using the public
API at `https://data.opm.gov/api/v1/files`. No key is needed. The files are
parquet, about 50 to 75 MB per month for employment and under 5 MB for
separations. They are not committed to the repo; rerun the script to get them.

The API serves a "current" version of each month. Agencies resubmit, so numbers
can shift slightly after a file is first published. This analysis used the
versions available on October 5, 2026.

## Baseline

Every "share of the workforce" comparison uses the January 2025 snapshot. That
is the last month before the deferred resignation offer went out, so it is the
population the offer was made to.

Agency headcount change is January 2025 against July 2026, the latest file
available.

## What counts as a buyout leaver

A separation record with `drp_indicator == "Y"`. The flag is set by the
employing agency when it files the action. If an agency coded a deferred
resignation as an ordinary retirement, it will not be counted here. There is
no way to check that from the outside.

The separations file is a list of personnel actions, not people. A person with
two separation actions in the window would be counted twice. That should be
rare for the buyout since it ends employment, but the counts are of actions.

## Things that are missing or redacted

- Duty station state is redacted for essentially all of the Army, Navy, Air
  Force, Defense, and most of DHS and Justice. Across the civilian agencies the
  redaction rate is about 9 percent. Nothing in this repo is broken down by
  state for that reason.
- Pay is redacted on 45 percent of buyout records, following the same agency
  pattern. The salary chart compares only records where pay is present, for
  both the leavers and the baseline workforce.
- The occupational category field reads "NO DATA REPORTED" on 85 percent of
  buyout records. It is not used. The STEM/health flag, which OPM derives from
  the occupational series code, is populated and stands in for it.
- OPM notes that a change in Department of War data processing kept some
  defense components from submitting June and July 2026 employment data. The
  July 2026 headcount is therefore a slight undercount for those agencies. The
  agency change chart should be read with that in mind for Army, Navy, Air
  Force and Defense. The files still label these agencies with their former
  names and this repo does the same.

## Choices made in the charts

- Agency charts only show agencies with at least 5,000 employees in January
  2025. Small agencies and commissions have large percentage swings on tiny
  bases and would crowd out the picture.
- Years of service and pay are cut into bands by hand. The bin edges are in
  `src/analysis.py` and are easy to change.
- Separations are plotted by the month of the file they appear in, which is
  the month the action was processed. The effective date can differ by a
  month or so.

## Reproducing

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/fetch.py          # about 1.3 GB, takes a few minutes
python src/analysis.py       # writes csv tables to output/
python src/charts.py         # writes pngs to output/
```
