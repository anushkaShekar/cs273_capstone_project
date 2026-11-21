from sklearn.metrics.pairwise import cosine_similarity

# Model 1: TF-IDF + Cosine Similarity
# Define a TF-IDF vectorizer that treats each skill as one unit
def split_skills(text):
    return text.split(" | ")

def recommender_one(user_skills, tfidf_vectorizer, tfidf_matrix, feature_names, occupation_profiles, top_n=5):
    # Convert user's skills to lowercase and keep only skills that exist in the data
    user_skills = [skill.lower() for skill in user_skills]
    matched = [s for s in user_skills if s in feature_names]

    if not matched:
        return []

    # Create a TF-IDF embedding for the user's skills (transform only)
    user_vector = tfidf_vectorizer.transform([" | ".join(matched)])

    # Cosine similarity: score each job from 0 (no overlap) to 1 (same skills)
    scores = cosine_similarity(user_vector, tfidf_matrix).flatten()
    top_jobs = scores.argsort()[::-1][:top_n]

    # Collect results
    results = []
    for job in top_jobs:
        job_skills = occupation_profiles.loc[job, "skill_profile"].lower().split(" | ")
        results.append({
            "occupation_title": occupation_profiles.loc[job, "occupation_title"],
            "score": round(float(scores[job]), 3),
            "matching_skills": [s for s in matched if s in job_skills]
        })

    return results