# Software Skills Job Recommender

A web app that recommends jobs based on the software skills a user picks.

The user picks skills from a dropdown and chooses a matching style. The backend compares the skills to each occupation's skill profile and returns the closest jobs.

## Project structure

```
├── frontend/              React (Vite) app
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── App.css
├── backend/               FastAPI API
│   ├── main.py            Endpoints: /skills and /recommend
│   ├── recommender.py     Recommender models
│   ├── requirements.txt
│   └── data/
│       └── occupation_skill_profiles.csv
├── scripts/
│   └── smoke_test.py      Quick check that the backend endpoints work
└── data_preprocessing.ipynb   Cleans the raw data (runs in Google Colab)
```

## How it works

1. **Preprocessing** (notebook): cleans the O*NET Software Skills data, keeps the target occupations, drops skills used by fewer than 2 occupations, and builds one skill profile per occupation. The output is `occupation_skill_profiles.csv`.
2. **Backend:** loads the profiles when it starts and builds the models.
3. **Frontend:** the user picks skills and a matching style, then clicks "Find jobs". The backend returns the closest jobs.

## Models

| Model | Method | Status |
|---|---|---|
| 1 | TF-IDF + cosine similarity | Done |
| 2 | TF-IDF + SVD + k-means | In progress |
| 3 | Transformer embeddings | In progress |

## API

| Endpoint | Method | Description |
|---|---|---|
| `/skills` | GET | Returns all skills, for the dropdown |
| `/recommend` | POST | Takes `{"skills": [...], "model": "one"}` (or `"two"`) and returns the top jobs |

## Running the app

You need Python 3 and Node.js. Run the backend and the frontend in two separate terminals.

**Backend** (from `backend/`):

```
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Test it at `http://localhost:8000/docs`.

**Frontend** (from `frontend/`):

```
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

**Smoke test** (from the repo root, with the backend running):

```
python scripts/smoke_test.py
```

## Troubleshooting

**The frontend page won't load**

1. Open `http://127.0.0.1:5173` instead of `localhost`.
2. Make sure `frontend/vite.config.js` has this line:
   ```javascript
   server: { host: "127.0.0.1", port: 5173, strictPort: true },
   ```
3. Check that no old servers are still running. If either command prints a process, stop it with `kill -9 <PID>`:
   ```
   lsof -i :8000
   lsof -i :5173
   ```
4. Reinstall the frontend packages from `frontend/`:
   ```
   rm -rf node_modules package-lock.json
   npm install
   npm run dev
   ```

**The skills dropdown is empty**

- Check that the backend is running and that `http://127.0.0.1:8000/skills` returns a list.
- Check that `API_URL` in `frontend/src/App.jsx` matches the backend address.

## Data

The data comes from the [O*NET](https://www.onetcenter.org/) Software Skills file. The raw file is kept in Google Drive because of its size. Only `occupation_skill_profiles.csv` is needed to run the app.


## AI Usage
Vibe coded with Anthropic Claude
