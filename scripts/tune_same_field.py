"""Review the Same field settings: number of skill groups (SVD components) and clusters.

Uses the app's Same field recommender and the same simulated users as evaluate.py.
Each setting is fit with three k-means seeds. Results are saved as a CSV and three charts.
Nothing is written to the metrics log.

Run from the repo root (takes a few minutes):
    python scripts/tune_same_field.py --related related_occupations.csv --out-dir tuning_results
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from recommender import recommender_two, split_skills  # noqa: E402

SKILL_GROUPS = [25, 50, 100, 200, 300]
CLUSTERS = [10, 15, 20, 30, 40, 60, 80]
APP_CLUSTER_OPTIONS = [10, 15, 20, 30, 40]
APP_SKILL_GROUPS = 100
APP_CLUSTERS = 40
KMEANS_SEEDS = [42, 0, 1]
QUERY_SEEDS = [0, 1, 2]
QUERY_SIZE = 10
TOP_JOBS = 5

TEAL, INK, MUTED, GRID, ACCENT = "#17667A", "#22313A", "#5B6B73", "#E3E8EA", "#B4531F"


def simulated_users(profiles, related):
    codes = profiles["occupation_code"].tolist()
    code_set = set(codes)
    titles = dict(zip(codes, profiles["occupation_title"]))
    skills = {c: p.lower().split(" | ") for c, p in zip(codes, profiles["skill_profile"])}
    users = []
    for seed in QUERY_SEEDS:
        rng = np.random.default_rng(seed)
        for code in codes:
            relevant = {titles[c] for c in (related.get(code, set()) & code_set) - {code}}
            if not relevant:
                continue
            pool = skills[code]
            query = sorted(rng.choice(pool, size=min(QUERY_SIZE, len(pool)), replace=False).tolist())
            users.append((code, titles[code], query, relevant))
    return users


def precision(users, model, profiles):
    by_source = {}
    for code, title, query, relevant in users:
        results = [r for r in recommender_two(query, model, profiles, top_n=TOP_JOBS + 1)
                   if r["occupation_title"] != title][:TOP_JOBS]
        hits = sum(r["occupation_title"] in relevant for r in results)
        by_source.setdefault(code, []).append(hits / TOP_JOBS)
    return float(np.mean([np.mean(v) for v in by_source.values()]))


def evaluate_setting(tfidf, svd_by_groups, groups, clusters, users, profiles):
    svd, svd_matrix = svd_by_groups[groups]
    scores, silhouettes = [], []
    for seed in KMEANS_SEEDS:
        kmeans = KMeans(n_clusters=clusters, random_state=seed, n_init=10).fit(svd_matrix)
        model = {"vectorizer": tfidf, "svd": svd, "svd_matrix": svd_matrix, "kmeans": kmeans}
        scores.append(precision(users, model, profiles))
        silhouettes.append(silhouette_score(svd_matrix, kmeans.labels_, metric="cosine"))
    return {
        "skill_groups": groups,
        "clusters": clusters,
        "variance_kept": float(svd.explained_variance_ratio_.sum()),
        "precision": float(np.mean(scores)),
        "precision_min": min(scores),
        "precision_max": max(scores),
        "silhouette": float(np.mean(silhouettes)),
    }


def line_chart(frame, x, y, xlabel, ylabel, chosen, path, ylim, percent=True, note=None, shade=None):
    fig, ax = plt.subplots(figsize=(4.6, 3.0), dpi=300)
    pos = np.arange(len(frame))
    scale = 100 if percent else 1
    values = frame[y].to_numpy() * scale
    if shade is not None:
        inside = [i for i, v in enumerate(frame[x]) if v in shade]
        ax.axvspan(min(inside) - 0.4, max(inside) + 0.4, color=GRID, alpha=0.6, lw=0)
        ax.text(min(inside) - 0.3, 0.97, "Options the app tests", transform=ax.get_xaxis_transform(),
                fontsize=7.5, color=MUTED, va="top")
    if "precision_min" in frame and percent:
        low = frame["precision_min"].to_numpy() * 100
        high = frame["precision_max"].to_numpy() * 100
        ax.vlines(pos, low, high, color=MUTED, lw=1.2, alpha=0.8)
    ax.plot(pos, values, color=TEAL, lw=2, marker="o", markersize=5, zorder=3)
    best = int(np.flatnonzero(frame[x].to_numpy() == chosen)[0])
    ax.plot(pos[best], values[best], marker="o", markersize=9, color=ACCENT, zorder=4)
    for i, v in enumerate(values):
        ax.text(pos[i] + 0.12, v, f"{v:.1f}%" if percent else f"{v:.2f}",
                ha="left", va="bottom", fontsize=7.5, color=INK)
    ax.set_xticks(pos, [str(v) for v in frame[x]])
    ax.set_xlim(-0.5, len(frame) - 0.3)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(*ylim)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    if note:
        fig.text(0.01, 0.01, note, fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.05 if note else 0, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--related", required=True, help="O*NET related_occupations.csv")
    parser.add_argument("--out-dir", default=str(ROOT / "tuning_results"))
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    profiles = pd.read_csv(ROOT / "backend" / "data" / "occupation_skill_profiles.csv")
    rel = pd.read_csv(args.related)
    rel = rel[rel["Relatedness Tier"].str.startswith("Primary")]
    related = rel.groupby("O*NET-SOC Code")["Related O*NET-SOC Code"].apply(set).to_dict()
    users = simulated_users(profiles, related)

    tfidf = TfidfVectorizer(tokenizer=split_skills, lowercase=True, token_pattern=None)
    tfidf_matrix = tfidf.fit_transform(profiles["skill_profile"])
    svd_by_groups = {}
    for groups in sorted(set(SKILL_GROUPS) | {APP_SKILL_GROUPS}):
        svd = TruncatedSVD(n_components=groups, random_state=42)
        svd_by_groups[groups] = (svd, normalize(svd.fit_transform(tfidf_matrix)))

    rows = []
    for groups in SKILL_GROUPS:
        rows.append({"review": "skill_groups", **evaluate_setting(tfidf, svd_by_groups, groups, APP_CLUSTERS, users, profiles)})
        print(f"{groups} skill groups: precision {rows[-1]['precision']:.4f}", flush=True)
    for clusters in CLUSTERS:
        rows.append({"review": "clusters", **evaluate_setting(tfidf, svd_by_groups, APP_SKILL_GROUPS, clusters, users, profiles)})
        print(f"{clusters} clusters: precision {rows[-1]['precision']:.4f} silhouette {rows[-1]['silhouette']:.3f}", flush=True)

    table = pd.DataFrame(rows)
    table.to_csv(out / "same_field_tuning.csv", index=False)
    seeds = f"Dots: average of {len(KMEANS_SEEDS)} k-means seeds. Gray lines: lowest to highest seed."

    groups = table[table["review"] == "skill_groups"].reset_index(drop=True)
    line_chart(groups, "skill_groups", "precision", "Number of skill groups (SVD components)",
               "Same field precision (%)", APP_SKILL_GROUPS, out / "skill_groups_precision.png", (15, 25),
               note=f"{APP_CLUSTERS} clusters. {seeds}")

    clusters = table[table["review"] == "clusters"].reset_index(drop=True)
    line_chart(clusters, "clusters", "silhouette", "Number of clusters", "Silhouette score",
               APP_CLUSTERS, out / "clusters_silhouette.png", (0.10, 0.30), percent=False, shade=APP_CLUSTER_OPTIONS,
               note=f"{APP_SKILL_GROUPS} skill groups. Average of {len(KMEANS_SEEDS)} k-means seeds.")
    line_chart(clusters, "clusters", "precision", "Number of clusters", "Same field precision (%)",
               APP_CLUSTERS, out / "clusters_precision.png", (15, 25), shade=APP_CLUSTER_OPTIONS,
               note=f"{APP_SKILL_GROUPS} skill groups. {seeds}")

    print(f"\nSaved results and charts to {out}")


if __name__ == "__main__":
    main()
