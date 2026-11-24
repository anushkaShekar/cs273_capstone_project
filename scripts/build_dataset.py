"""Build the app's occupation skill profiles from the O*NET Software Skills file.

Keeps occupations with at least 10 skills, drops skills used by only one of those
occupations, and writes one row per occupation.

Run from the repo root:
    python scripts/build_dataset.py --skills software_skills.csv
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MIN_SKILLS = 10
MIN_OCCUPATIONS = 2


def build_profiles(raw):
    raw = raw.assign(skill=raw["Workplace Example"].str.lower().str.strip())
    raw = raw.drop_duplicates(["O*NET-SOC Code", "skill"])

    # Keep occupations with enough skills to describe them
    sizes = raw.groupby("O*NET-SOC Code")["skill"].nunique()
    rows = raw[raw["O*NET-SOC Code"].isin(sizes[sizes >= MIN_SKILLS].index)]

    # Drop skills that can't connect one occupation to another
    counts = rows.groupby("skill")["O*NET-SOC Code"].nunique()
    rows = rows[rows["skill"].isin(counts[counts >= MIN_OCCUPATIONS].index)]

    table = (rows.sort_values("skill")
             .groupby(["O*NET-SOC Code", "Title"])["skill"]
             .agg(" | ".join).reset_index())
    table.columns = ["occupation_code", "occupation_title", "skill_profile"]
    table["skill_count"] = table["skill_profile"].str.count(r" \| ") + 1
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skills", required=True, help="O*NET software_skills.csv")
    parser.add_argument("--out", default=str(ROOT / "backend" / "data" / "occupation_skill_profiles.csv"))
    args = parser.parse_args()

    table = build_profiles(pd.read_csv(args.skills))
    table.to_csv(args.out, index=False)
    print(f"Wrote {len(table)} occupations to {args.out}")


if __name__ == "__main__":
    main()
