from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from collections import Counter
import math
import numpy as np

def split_skills(text):
    return text.split(" | ")

# Lowercase the user's skills and keep only the ones that exist in the data
def match_skills(user_skills, feature_names):
    known = set(feature_names)
    user_skills = [skill.lower() for skill in user_skills]
    return [s for s in user_skills if s in known]

# Average the embeddings of individual skills, so long profiles are never cut off
def embed_skills(skills, skill_vectors):
    vector = np.mean([skill_vectors[s] for s in skills], axis=0)
    return vector / np.linalg.norm(vector)

# Pick the best-scoring jobs, leaving out jobs with no similarity to the user
def top_jobs(scores, top_n):
    order = np.argsort(-scores, kind="stable")
    return order[scores[order] > 0][:top_n]

# Turn job row numbers and their scores into a list of results
def build_results(jobs, scores, matched, occupation_profiles):
    results = []
    for job, score in zip(jobs, scores):
        job_skills = occupation_profiles.loc[job, "skill_profile"].lower().split(" | ")
        results.append({
            "occupation_title": occupation_profiles.loc[job, "occupation_title"],
            "score": round(float(score), 3),
            "matching_skills": [s for s in matched if s in job_skills]
        })
    return results

# Model 1: TF-IDF + Cosine Similarity
def recommender_one(user_skills, model_one, occupation_profiles, top_n=5):
    tfidf_vectorizer = model_one["vectorizer"]
    tfidf_matrix = model_one["tfidf_matrix"]
    feature_names = tfidf_vectorizer.get_feature_names_out()

    matched = match_skills(user_skills, feature_names)
    if not matched:
        return []

    # Create a TF-IDF embedding for the user's skills (transform only)
    user_vector = tfidf_vectorizer.transform([" | ".join(matched)])

    # Cosine similarity: score each job from 0 (no overlap) to 1 (same skills)
    scores = cosine_similarity(user_vector, tfidf_matrix).flatten()
    best = top_jobs(scores, top_n)

    return build_results(best, scores[best], matched, occupation_profiles)

# Model 2: SVD + K-means, searching only the jobs in the user's field (cluster)
def recommender_two(user_skills, model_two, occupation_profiles, top_n=5):
    tfidf_vectorizer = model_two["vectorizer"]
    svd = model_two["svd"]
    svd_matrix = model_two["svd_matrix"]
    kmeans = model_two["kmeans"]
    feature_names = tfidf_vectorizer.get_feature_names_out()

    matched = match_skills(user_skills, feature_names)
    if not matched:
        return []

    # Create a TF-IDF embedding for the user's skills, shrink it with SVD (transform only),
    # and normalize it so a short skill list is not pulled toward the wrong cluster
    user_vector = tfidf_vectorizer.transform([" | ".join(matched)])
    user_svd = normalize(svd.transform(user_vector))

    # Find the user's cluster and the jobs that belong to it
    user_cluster = kmeans.predict(user_svd)[0]
    cluster_jobs = np.where(kmeans.labels_ == user_cluster)[0]

    # Cosine similarity: score only the jobs in the user's cluster
    scores = cosine_similarity(user_svd, svd_matrix[cluster_jobs]).flatten()
    best = top_jobs(scores, top_n)

    return build_results(cluster_jobs[best], scores[best], matched, occupation_profiles)

# Model 3: all-MiniLM-L6-v2, embedding each skill separately
def recommender_three(user_skills, model_three, occupation_profiles, top_n=5):
    feature_names = model_three["feature_names"]
    matched = match_skills(user_skills, feature_names)

    if not matched:
        return []

    # Create an embedding for the user's skills
    user_vector = embed_skills(matched, model_three["skill_vectors"]).reshape(1, -1)

    # Cosine similarity: score each job by how close its skills are to the user's
    scores = cosine_similarity(user_vector, model_three["embeddings"]).flatten()
    best = top_jobs(scores, top_n)

    return build_results(best, scores[best], matched, occupation_profiles)

# Add each recommended job's full skill list for the expandable view:
# the user's skills come first, then the skills used by the fewest jobs overall
def add_job_skills(results, user_skills, occupation_profiles):
    user_skills = {skill.lower() for skill in user_skills}
    profiles = {
        title: set(profile.lower().split(" | "))
        for title, profile in zip(occupation_profiles["occupation_title"], occupation_profiles["skill_profile"])
    }
    job_counts = Counter(skill for profile in profiles.values() for skill in profile)

    for job in results:
        ordered = sorted(
            profiles[job["occupation_title"]],
            key=lambda skill: (skill not in user_skills, job_counts[skill], skill)
        )
        job["job_skills"] = [{"skill": skill, "has": skill in user_skills} for skill in ordered]
    return results

# Rank the skills the user is missing with a class-based TF-IDF variant:
#   importance = share of the returned jobs with the skill * log(1 + all jobs / jobs with the skill)
# Only the jobs this search returned count toward the share, so each mode's results
# drive its own list. The "1 +" keeps widely used skills from dropping to a score of zero.
def missing_skills(results, user_skills, occupation_profiles, top_n=10):
    if not results:
        return []

    user_skills = {skill.lower() for skill in user_skills}
    profiles = [set(p.lower().split(" | ")) for p in occupation_profiles["skill_profile"]]
    titles = occupation_profiles["occupation_title"].tolist()
    recommended = [titles.index(job["occupation_title"]) for job in results]

    # How many jobs in the whole dataset use each skill
    job_counts = Counter(skill for profile in profiles for skill in profile)

    # Skills the returned jobs use that the user doesn't have
    recommended_counts = Counter()
    for job in recommended:
        recommended_counts.update(profiles[job] - user_skills)

    ranked = []
    for skill, jobs in recommended_counts.items():
        idf = math.log(1 + len(profiles) / job_counts[skill])
        tf = jobs / len(recommended)
        ranked.append({"skill": skill, "jobs": jobs, "importance": round(tf * idf, 3)})

    # The skill name is the final tie-breaker, so results never change between runs
    ranked.sort(key=lambda item: (-item["importance"], -item["jobs"], item["skill"]))
    return ranked[:top_n]
