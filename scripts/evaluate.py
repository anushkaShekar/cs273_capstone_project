"""Compare the original and current recommenders, and log the metrics.

Each simulated user holds 10 skills sampled from one occupation. That occupation
is hidden from the results, and the top 5 jobs are scored against O*NET's Primary
related occupations. Skill suggestions are scored by how many belong to the
hidden occupation. Every run appends one timestamped line to the metrics log.

Run from the repo root:
    python scripts/evaluate.py --related related_occupations.csv
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import recommender as current  # noqa: E402
from models import build_models, choose_clusters  # noqa: E402

TOP_JOBS = 5
TOP_SKILLS = 10
QUERY_SIZE = 10
SEEDS = [0, 1, 2]


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


# Load the recommender code as it was at an earlier commit
def load_original(ref):
    module = types.ModuleType("original_recommender")
    exec(git("show", f"{ref}:backend/recommender.py"), module.__dict__)
    return module


def score_jobs(titles, relevant):
    hits = [int(t in relevant) for t in titles[:TOP_JOBS]]
    ideal = sum(1 / np.log2(i + 2) for i in range(min(TOP_JOBS, len(relevant))))
    dcg = sum(hit / np.log2(i + 2) for i, hit in enumerate(hits))
    return {"p5": sum(hits) / TOP_JOBS, "hit5": float(any(hits)), "ndcg5": dcg / ideal, "returned": len(hits)}


def summarize(rows, sources):
    boot = np.random.default_rng(0)
    frame = pd.DataFrame(rows).groupby("source").mean(numeric_only=True).loc[sources]
    samples = [frame["p5"].values[boot.integers(0, len(frame), len(frame))].mean() for _ in range(2000)]
    summary = {name: round(float(frame[name].mean()), 4) for name in frame.columns}
    summary["p5_ci95"] = [round(float(np.percentile(samples, 2.5)), 4), round(float(np.percentile(samples, 97.5)), 4)]
    return summary


def evaluate_scope(profiles, related, encoder, original):
    profiles = profiles.reset_index(drop=True)
    start = time.perf_counter()
    fitted = build_models(profiles, encoder)
    fit_seconds = time.perf_counter() - start
    labels = fitted["cluster_labels"]

    # The original Model 2 clusters the SVD vectors without normalizing them
    svd = fitted["two"]["svd"]
    original_matrix = svd.transform(fitted["one"]["tfidf_matrix"])
    original_k = choose_clusters(original_matrix)
    original_two = {
        **fitted["two"],
        "svd_matrix": original_matrix,
        "kmeans": KMeans(n_clusters=original_k, random_state=42, n_init=10).fit(original_matrix),
    }

    # The original Model 3 embeds each job's skills as one long text
    joined = profiles["skill_profile"].str.lower().str.replace(" | ", ", ", regex=False).tolist()
    original_three = {
        "model": encoder,
        "embeddings": normalize(encoder.encode(joined, batch_size=64)),
        "feature_names": fitted["feature_names"],
    }

    def original_gaps(results, query):
        return original.missing_skills(results, query, profiles, top_n=TOP_SKILLS)

    def current_gaps(results, query):
        return current.missing_skills(results, query, profiles, top_n=TOP_SKILLS)

    variants = {
        ("one", "before"): (original.recommender_one, fitted["one"], original_gaps),
        ("two", "before"): (original.recommender_two, original_two, original_gaps),
        ("three", "before"): (original.recommender_three, original_three, original_gaps),
        ("one", "after"): (current.recommender_one, fitted["one"], current_gaps),
        ("two", "after"): (current.recommender_two, fitted["two"], current_gaps),
        ("three", "after"): (current.recommender_three, fitted["three"], current_gaps),
    }

    codes = profiles["occupation_code"].tolist()
    title_of = dict(zip(codes, profiles["occupation_title"]))
    skills_of = {c: p.lower().split(" | ") for c, p in zip(codes, profiles["skill_profile"])}
    sources = [c for c in codes if (related.get(c, set()) & set(codes)) - {c}]
    rows = {key: [] for key in variants}
    latency = {key: [] for key in variants}
    digest = hashlib.sha256()

    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        for source in sources:
            pool = skills_of[source]
            query = sorted(rng.choice(pool, size=min(QUERY_SIZE, len(pool)), replace=False).tolist())
            relevant = {title_of[c] for c in (related[source] & set(codes)) - {source}}
            truth = set(pool) - set(query)

            for key, (recommend, model, gaps) in variants.items():
                tick = time.perf_counter()
                results = [r for r in recommend(query, model, profiles, top_n=TOP_JOBS + 1)
                           if r["occupation_title"] != title_of[source]][:TOP_JOBS]
                suggested = gaps(results, query)
                latency[key].append((time.perf_counter() - tick) * 1000)

                row = score_jobs([r["occupation_title"] for r in results], relevant)
                row["source"] = source
                row["skill_p10"] = (sum(s["skill"] in truth for s in suggested) / len(suggested)) if suggested else 0.0
                rows[key].append(row)
                if key[1] == "after":
                    digest.update(json.dumps([results, suggested], sort_keys=True).encode())

    job_total = len(codes)
    random_p5 = np.mean([len((related[c] & set(codes)) - {c}) / (job_total - 1) for c in sources])
    models = []
    for (model, version), model_rows in rows.items():
        models.append({"model": model, "version": version, **summarize(model_rows, sources),
                       "latency_ms": round(float(np.mean(latency[(model, version)])), 2)})
    return {
        "occupations": job_total,
        "sources": len(sources),
        "skills": len(fitted["feature_names"]),
        "clusters": int(labels.max() + 1),
        "smallest_cluster": int(np.bincount(labels).min()),
        "svd_components": int(fitted["two"]["svd"].n_components),
        "svd_explained_variance": round(float(fitted["two"]["svd"].explained_variance_ratio_.sum()), 4),
        "fit_seconds": round(fit_seconds, 2),
        "random_p5": round(float(random_p5), 4),
        "after_results_sha256": digest.hexdigest(),
        "models": models,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--related", required=True, help="O*NET related_occupations.csv")
    parser.add_argument("--onet-version", default="31.0")
    parser.add_argument("--baseline-ref", default="ccb6ae3", help="commit holding the original recommender")
    parser.add_argument("--log", default=str(ROOT / "backend" / "metrics" / "metrics_log.jsonl"))
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    started = time.perf_counter()
    rel = pd.read_csv(args.related)
    rel = rel[rel["Relatedness Tier"].str.startswith("Primary")]
    related = rel.groupby("O*NET-SOC Code")["Related O*NET-SOC Code"].apply(set).to_dict()

    shipped = pd.read_csv(ROOT / "backend" / "data" / "occupation_skill_profiles.csv")
    scopes = {"expanded_min10": shipped}

    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    original = load_original(args.baseline_ref)
    results = {}
    for name, table in scopes.items():
        print(f"Evaluating {name} ({len(table)} occupations)...", flush=True)
        results[name] = evaluate_scope(table, related, encoder, original)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": args.note,
        "git": {
            "branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
            "commit": git("rev-parse", "--short", "HEAD").strip(),
            "uncommitted_changes": bool(git("status", "--porcelain", "--", "backend", "scripts").strip()),
            "baseline_ref": args.baseline_ref,
        },
        "config": {
            "onet_version": args.onet_version,
            "query_skills": QUERY_SIZE,
            "top_jobs": TOP_JOBS,
            "top_skills": TOP_SKILLS,
            "seeds": SEEDS,
            "relevance": "O*NET Primary related occupations",
            "python_hash_seed": os.environ.get("PYTHONHASHSEED", "random"),
        },
        "runtime_seconds": round(time.perf_counter() - started, 1),
        "scopes": results,
    }

    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as handle:
        handle.write(json.dumps(record) + "\n")

    for name, scope in results.items():
        print(f"\n{name}: {scope['occupations']} jobs, k={scope['clusters']}, random P@5={scope['random_p5']}")
        for m in scope["models"]:
            print(f"  {m['model']:5s} {m['version']:6s} P@5 {m['p5']:.3f} {m['p5_ci95']} hit@5 {m['hit5']:.3f} "
                  f"nDCG@5 {m['ndcg5']:.3f} returned {m['returned']:.2f} skill P@10 {m['skill_p10']:.3f} "
                  f"{m['latency_ms']:.1f} ms")
    print(f"\nLogged to {log} at {record['timestamp_utc']} ({record['runtime_seconds']}s)")


if __name__ == "__main__":
    main()
