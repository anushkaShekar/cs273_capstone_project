import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

from recommender import embed_skills, split_skills

# Candidate cluster counts when the dataset is larger than the original 12 jobs
CLUSTER_OPTIONS = [10, 15, 20, 30, 40]


# Pick the cluster count with the best silhouette score
def choose_clusters(svd_matrix):
    options = [k for k in CLUSTER_OPTIONS if k < len(svd_matrix)]
    scores = {}
    for k in options:
        labels = KMeans(n_clusters=k, random_state=42, n_init=5).fit_predict(svd_matrix)
        scores[k] = silhouette_score(svd_matrix, labels, metric="cosine")
    return max(scores, key=scores.get)


# Fit all three models on a table of occupation skill profiles
def build_models(occupation_profiles, transformer):
    # Define a TF-IDF vectorizer that treats each skill as one unit
    tfidf_vectorizer = TfidfVectorizer(
        tokenizer=split_skills,
        lowercase=True,
        token_pattern=None
    )

    # Learn the skills from the job profiles and convert each job into a row of numbers
    tfidf_matrix = tfidf_vectorizer.fit_transform(occupation_profiles["skill_profile"])

    # Get the list of skills (one per column)
    feature_names = tfidf_vectorizer.get_feature_names_out()

    # Model 1: bundle the fitted pieces
    model_one = {"vectorizer": tfidf_vectorizer, "tfidf_matrix": tfidf_matrix}

    # Model 2: shrink with SVD, group the jobs with k-means
    job_count = len(occupation_profiles)
    n_components = 5 if job_count <= 12 else min(100, job_count - 1, tfidf_matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    svd_matrix = svd.fit_transform(tfidf_matrix)
    n_clusters = 3 if job_count <= 12 else choose_clusters(svd_matrix)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit(svd_matrix)

    model_two = {"vectorizer": tfidf_vectorizer, "svd": svd, "svd_matrix": svd_matrix, "kmeans": kmeans}

    # Model 3: embed each skill, then average the skills in each job
    skill_embeddings = normalize(transformer.encode(feature_names.tolist(), batch_size=256))
    skill_vectors = dict(zip(feature_names.tolist(), skill_embeddings))
    job_skills = occupation_profiles["skill_profile"].str.lower().str.split(" | ", regex=False)
    job_embeddings = np.vstack([embed_skills(skills, skill_vectors) for skills in job_skills])

    model_three = {
        "model": transformer,
        "embeddings": job_embeddings,
        "feature_names": feature_names,
        "skill_vectors": skill_vectors
    }

    return {
        "one": model_one,
        "two": model_two,
        "three": model_three,
        "feature_names": feature_names,
        "cluster_labels": kmeans.labels_
    }
