import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from models import build_models
from recommender import recommender_one, recommender_two, recommender_three, missing_skills, add_job_skills

METRICS_LOG = Path(__file__).parent / "metrics" / "metrics_log.jsonl"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load the data
occupation_profiles = pd.read_csv("data/occupation_skill_profiles.csv")

# Fit the three models
transformer = SentenceTransformer("all-MiniLM-L6-v2")
models = build_models(occupation_profiles, transformer)
model_one = models["one"]
model_two = models["two"]
model_three = models["three"]
feature_names = models["feature_names"]

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
        "results": add_job_skills(results, request.skills, occupation_profiles),
        "skills_to_learn": missing_skills(results, request.skills, occupation_profiles)
    }

# /metrics (GET): returns every logged evaluation run, oldest first
@app.get("/metrics")
async def get_metrics():
    if not METRICS_LOG.exists():
        return {"runs": []}
    with METRICS_LOG.open() as log:
        return {"runs": [json.loads(line) for line in log if line.strip()]}
