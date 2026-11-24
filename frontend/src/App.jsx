import { useEffect, useState } from "react";
import "./App.css";
import SkillPicker from "./components/SkillPicker.jsx";
import ModelPicker from "./components/ModelPicker.jsx";
import JobResults from "./components/JobResults.jsx";
import SkillsToLearn from "./components/SkillsToLearn.jsx";
import Dashboard from "./components/Dashboard.jsx";

// Address of the backend API
const API_URL = "http://127.0.0.1:8000";

export default function App() {
  const [view, setView] = useState("recommender");        // which tab is showing
  const [allSkills, setAllSkills] = useState([]);         // every skill from the backend
  const [selected, setSelected] = useState([]);           // skills the user picked
  const [model, setModel] = useState("one");              // matching style the user picked
  const [results, setResults] = useState(null);           // null = no search yet
  const [skillsToLearn, setSkillsToLearn] = useState([]); // skills the user does not have yet
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load the skill list once when the page opens
  useEffect(() => {
    fetch(`${API_URL}/skills`)
      .then((res) => res.json())
      .then((data) => setAllSkills(data.skills))
      .catch(() =>
        setError("Could not load skills. Check that the backend is running.")
      );
  }, []);

  function addSkill(skill) {
    setSelected([...selected, skill]);
  }

  function removeSkill(skill) {
    setSelected(selected.filter((s) => s !== skill));
  }

  // Switching the matching style clears old results, so they never look mismatched
  function changeModel(id) {
    setModel(id);
    setResults(null);
    setSkillsToLearn([]);
  }

  // Send the picked skills and matching style to the backend
  async function getRecommendations() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skills: selected, model }),
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      setResults(data.results);
      setSkillsToLearn(data.skills_to_learn || []);
    } catch {
      setError("Could not get recommendations. Check that the backend is running.");
    }
    setLoading(false);
  }

  return (
    <main className={view === "dashboard" ? "page wide" : "page"}>
      <nav className="tabs" aria-label="Pages">
        <button
          className={view === "recommender" ? "tab active" : "tab"}
          aria-current={view === "recommender" ? "page" : undefined}
          onClick={() => setView("recommender")}
        >
          Recommender
        </button>
        <button
          className={view === "dashboard" ? "tab active" : "tab"}
          aria-current={view === "dashboard" ? "page" : undefined}
          onClick={() => setView("dashboard")}
        >
          Model performance
        </button>
      </nav>

      {view === "dashboard" ? (
        <>
          <header className="intro-block">
            <h1>Model performance</h1>
            <p className="intro">
              How well each model finds related jobs.
            </p>
          </header>
          <Dashboard apiUrl={API_URL} />
        </>
      ) : (
        <>
          <header className="intro-block">
            <h1>What's next in your tech career?</h1>
            <p className="intro">
              Tell us your skills. We'll suggest jobs to aim for and skills to add.
            </p>
          </header>

          {/* Inputs */}
          <section className="inputs">
            <SkillPicker
              allSkills={allSkills}
              selected={selected}
              onAdd={addSkill}
              onRemove={removeSkill}
            />

            <ModelPicker model={model} onChange={changeModel} />

            <button
              className="submit"
              onClick={getRecommendations}
              disabled={selected.length === 0 || loading}
            >
              {loading ? "Finding jobs..." : "Find jobs"}
            </button>

            {error && <p className="error">{error}</p>}
          </section>

          {/* Results */}
          {results && results.length === 0 && (
            <p className="empty">No matching jobs found. Try adding more skills.</p>
          )}

          {results && results.length > 0 && (
            <div className="results-area">
              <JobResults results={results} />
              <SkillsToLearn skills={skillsToLearn} jobCount={results.length} />
            </div>
          )}
        </>
      )}
    </main>
  );
}