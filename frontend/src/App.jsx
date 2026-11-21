import { useEffect, useState } from "react";
import "./App.css";

// Address of the backend API
const API_URL = "http://localhost:8000";

export default function App() {
  const [allSkills, setAllSkills] = useState([]); // every skill from the backend
  const [selected, setSelected] = useState([]);   // skills the user picked
  const [query, setQuery] = useState("");         // text typed in the search box
  const [open, setOpen] = useState(false);        // is the dropdown showing?
  const [results, setResults] = useState(null);   // null = no search yet
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

  // Skills that match the search text and are not already picked
  const options = allSkills
    .filter((s) => !selected.includes(s) && s.includes(query.toLowerCase()))
    .slice(0, 50);

  function addSkill(skill) {
    setSelected([...selected, skill]);
    setQuery("");
  }

  function removeSkill(skill) {
    setSelected(selected.filter((s) => s !== skill));
  }

  // Send the picked skills to the backend and show the top jobs
  async function getRecommendations() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skills: selected, model: "one" }),
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      setResults(data.results);
    } catch {
      setError("Could not get recommendations. Check that the backend is running.");
    }
    setLoading(false);
  }

  return (
    <main className="page">
      <h1>Find jobs that fit your skills</h1>
      <p className="intro">
        Pick the software skills you have. We will show the 5 closest jobs.
      </p>

      {/* Skill picker */}
      <div className="picker">
        <input
          type="text"
          placeholder="Search skills, e.g. python"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
        />
        {open && (
          <ul className="options">
            {options.length === 0 && <li className="none">No skills found</li>}
            {options.map((skill) => (
              // onMouseDown runs before the input loses focus
              <li key={skill} onMouseDown={() => addSkill(skill)}>
                {skill}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Picked skills */}
      <div className="chips">
        {selected.map((skill) => (
          <span className="chip" key={skill}>
            {skill}
            <button onClick={() => removeSkill(skill)} aria-label={`Remove ${skill}`}>
              ×
            </button>
          </span>
        ))}
      </div>

      <button
        className="submit"
        onClick={getRecommendations}
        disabled={selected.length === 0 || loading}
      >
        {loading ? "Finding jobs..." : "Find jobs"}
      </button>

      {error && <p className="error">{error}</p>}

      {/* Results */}
      {results && results.length === 0 && (
        <p className="empty">No matching jobs found. Try adding more skills.</p>
      )}

      {results && results.length > 0 && (
        <>
          <p className="note">
            Jobs are listed from closest to least close match. The tags under
            each job are your skills that it also uses.
          </p>
          <ol className="results">
            {results.map((job) => (
              <li key={job.occupation_title}>
                <div className="job-head">
                  <span className="job-title">{job.occupation_title}</span>
                </div>
                <div className="chips small">
                  {job.matching_skills.map((s) => (
                    <span className="chip" key={s}>{s}</span>
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </main>
  );
}
