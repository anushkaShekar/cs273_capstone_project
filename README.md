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

## Data

The data comes from the [O*NET](https://www.onetcenter.org/) Software Skills file. The raw file is kept in Google Drive because of its size. Only `occupation_skill_profiles.csv` is needed to run the app.

## AI Usage
Vibe coded with Anthropic Claude
