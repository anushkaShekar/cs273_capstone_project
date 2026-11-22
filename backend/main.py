import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans

from recommender import split_skills, recommender_one, recommender_two, recommender_three, missing_skills

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load the data
occupation_profiles = pd.read_csv("data/occupation_skill_profiles.csv")

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
svd = TruncatedSVD(n_components=5, random_state=42)
svd_matrix = svd.fit_transform(tfidf_matrix)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10).fit(svd_matrix)

model_two = {"vectorizer": tfidf_vectorizer, "svd": svd, "svd_matrix": svd_matrix, "kmeans": kmeans}

# Model 3: embed each job's skills with a pre-trained sentence transformer
transformer = SentenceTransformer("all-MiniLM-L6-v2")
job_texts = occupation_profiles["skill_profile"].str.lower().str.replace(" | ", ", ", regex=False)
job_embeddings = transformer.encode(job_texts.tolist())

model_three = {"model": transformer, "embeddings": job_embeddings, "feature_names": feature_names}

# Define the expected request body for /recommend: a list of skill names and the model to use
class SkillRequest(BaseModel):
    skills: list[str]
    model: str = "one"

# /skills (GET): returns all skills for the frontend dropdown
@app.get("/skills")
async def get_skills():
    return {"skills": feature_names.tolist()}

# /recommend (POST): takes the user's skills and model, returns the top matching jobs
@app.post("/recommend")
async def give_recommendation(request: SkillRequest):
    if request.model == "one":
        results = recommender_one(request.skills, model_one, occupation_profiles)
    elif request.model == "two":
        results = recommender_two(request.skills, model_two, occupation_profiles)
    elif request.model == "three":
        results = recommender_three(request.skills, model_three, occupation_profiles)
    else:
        return {"results": [], "skills_to_learn": [], "error": "Model not available yet."}

    return {
        "results": results,
        "skills_to_learn": missing_skills(results, request.skills, occupation_profiles)
    }

