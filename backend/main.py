import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer

from recommender import split_skills, recommender_one

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

# Define the expected request body for /recommend: a list of skill names
class SkillRequest(BaseModel):
    skills: list[str]
    model: str = "one"

# /skills (GET): returns all skills for the frontend dropdown
@app.get("/skills")
async def get_skills():
    return {"skills": feature_names.tolist()}

# /recommend (POST): takes the user's skills and model, returns the top 5 matching jobs
@app.post("/recommend")
async def give_recommendation(request: SkillRequest):
    # Run the model the user picked (only model one exists for now)
    if request.model == "one":
        results = recommender_one(
            request.skills,
            tfidf_vectorizer,
            tfidf_matrix,
            feature_names,
            occupation_profiles
        )
    else:
        return {"results": [], "error": "Model not available yet"}

    return {"results": results}


