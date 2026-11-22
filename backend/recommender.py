from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
import numpy as np

def split_skills(text):
    return text.split(" | ")

# Lowercase the user's skills and keep only the ones that exist in the data
def match_skills(user_skills, feature_names):
    user_skills = [skill.lower() for skill in user_skills]
    return [s for s in user_skills if s in feature_names]

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
    top_jobs = scores.argsort()[::-1][:top_n]

    return build_results(top_jobs, scores[top_jobs], matched, occupation_profiles)

# Model 2: SVD + K-means Clustering
def recommender_two(user_skills, model_two, occupation_profiles, top_n=5):
    tfidf_vectorizer = model_two["vectorizer"]
    svd = model_two["svd"]
    svd_matrix = model_two["svd_matrix"]
    kmeans = model_two["kmeans"]
    feature_names = tfidf_vectorizer.get_feature_names_out()

    matched = match_skills(user_skills, feature_names)
    if not matched:
        return []

    # Create a TF-IDF embedding for the user's skills, then shrink it with SVD (transform only)
    user_vector = tfidf_vectorizer.transform([" | ".join(matched)])
    user_svd = svd.transform(user_vector)

    # Find the user's cluster and the jobs that belong to it
    user_cluster = kmeans.predict(user_svd)[0]
    cluster_jobs = np.where(kmeans.labels_ == user_cluster)[0]

    # Cosine similarity: score only the jobs in the user's cluster
    scores = cosine_similarity(user_svd, svd_matrix[cluster_jobs]).flatten()
    top_positions = scores.argsort()[::-1][:top_n]

    return build_results(cluster_jobs[top_positions], scores[top_positions], matched, occupation_profiles)

# Model 3: all-MiniLM-L6-v2
def recommender_three(user_skills, model_three, occupation_profiles, top_n=5):
    feature_names = model_three["feature_names"]
    matched = match_skills(user_skills, feature_names)

    if not matched:
        return []

    # Create an embedding for the user's skills
    user_vector = model_three["model"].encode([", ".join(matched)])

    # Cosine similarity: score each job from 0 (no overlap) to 1 (same skills)
    scores = cosine_similarity(user_vector, model_three["embeddings"]).flatten()
    top_jobs = scores.argsort()[::-1][:top_n]

    return build_results(top_jobs, scores[top_jobs], matched, occupation_profiles)

# Count the skills the recommended jobs use that the user doesn't have
def missing_skills(results, user_skills, occupation_profiles, top_n=10):
    user_skills = {skill.lower() for skill in user_skills}
    titles = [job["occupation_title"] for job in results]
    top_profiles = occupation_profiles[occupation_profiles["occupation_title"].isin(titles)]

    counts = Counter()
    for profile in top_profiles["skill_profile"]:
        # 1. Turn the job's skill text into a list of skills
        job_skills = profile.lower().split(" | ")

        # 2. Remove repeats
        job_skills = set(job_skills)

        # 3. Remove the skills the user already has
        missing = job_skills - user_skills

        # 4. Add 1 to the count of each missing skill
        counts.update(missing)

    # Return the most common ones in the shape the frontend expects
    return [{"skill": skill, "jobs": n} for skill, n in counts.most_common(top_n)]