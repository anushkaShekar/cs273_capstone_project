import { useEffect, useState } from "react";

const MODELS = [
  { id: "one", name: "Model 1: TF-IDF" },
  { id: "two", name: "Model 2: SVD + k-means" },
  { id: "three", name: "Model 3: MiniLM embeddings" },
];

const METRICS = [
  { id: "p5", name: "Precision", help: "Share of the top 5 jobs that O*NET lists as related." },
  { id: "hit5", name: "Hit rate", help: "Share of users with at least one related job in the top 5." },
  { id: "ndcg5", name: "nDCG", help: "Like precision, but related jobs ranked higher count for more." },
];

const percent = (value) => `${(value * 100).toFixed(1)}%`;
const when = (timestamp) => new Date(timestamp).toLocaleString();

// The log also stores the original code's results, which the dashboard doesn't show
function find(scope, model) {
  return scope.models.find((m) => m.model === model && m.version === "after");
}

function Bar({ label, value, detail }) {
  return (
    <div className="bar-row" tabIndex={0} aria-label={`${label}: ${percent(value)}. ${detail}`}>
      <span className="bar-label">{label}</span>
      <span className="bar-track">
        <span className="bar-fill" style={{ width: `${value * 100}%` }} />
        <span className="bar-value" style={{ left: `${value * 100}%` }}>{percent(value)}</span>
      </span>
      <span className="bar-tip" role="tooltip">{label}: {percent(value)}. {detail}</span>
    </div>
  );
}

export default function Dashboard({ apiUrl }) {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState("");
  const [runIndex, setRunIndex] = useState(0);
  const [metricId, setMetricId] = useState("p5");

  useEffect(() => {
    fetch(`${apiUrl}/metrics`)
      .then((res) => {
        if (!res.ok) throw new Error("Request failed");
        return res.json();
      })
      .then((data) => {
        const newestFirst = [...data.runs].reverse();
        setRuns(newestFirst);
      })
      .catch(() => setError("Could not load metrics. Check that the backend is running."));
  }, [apiUrl]);

  if (error) return <p className="error">{error}</p>;
  if (!runs) return <p className="empty">Loading metrics...</p>;
  if (runs.length === 0) {
    return <p className="empty">No metrics yet. Run scripts/evaluate.py to create the first run.</p>;
  }

  const run = runs[runIndex];
  const scope = run.scopes.expanded_min10;
  const metric = METRICS.find((m) => m.id === metricId);
  const rows = MODELS.map((model) => ({ ...model, values: find(scope, model.id) }));
  const best = [...rows].sort((a, b) => b.values.p5 - a.values.p5)[0];

  return (
    <section className="dashboard">
      <div className="filters">
        <label>
          Evaluation run
          <select value={runIndex} onChange={(e) => setRunIndex(Number(e.target.value))}>
            {runs.map((r, i) => (
              <option key={r.timestamp_utc} value={i}>{when(r.timestamp_utc)}</option>
            ))}
          </select>
        </label>
        <label>
          Metric
          <select value={metricId} onChange={(e) => setMetricId(e.target.value)}>
            {METRICS.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </label>
      </div>

      <div className="tiles">
        <div className="tile">
          <span className="tile-label">Best model by precision</span>
          <span className="tile-value small">{best.name}</span>
        </div>
        <div className="tile">
          <span className="tile-label">Its precision</span>
          <span className="tile-value">{percent(best.values.p5)}</span>
        </div>
        <div className="tile">
          <span className="tile-label">Random baseline</span>
          <span className="tile-value">{percent(scope.random_p5)}</span>
        </div>
        <div className="tile">
          <span className="tile-label">Simulated users per run</span>
          <span className="tile-value">{(scope.sources * run.config.seeds.length).toLocaleString()}</span>
        </div>
      </div>

      <div className="chart-card">
        <h2>{metric.name} by model</h2>
        <p className="note">{metric.help}</p>
        <div className="bars">
          {rows.map((row) => (
            <Bar
              key={row.id}
              label={row.name}
              value={row.values[metricId]}
              detail={metricId === "p5"
                ? `95% CI ${percent(row.values.p5_ci95[0])} to ${percent(row.values.p5_ci95[1])}`
                : `Average of ${scope.sources} occupations`}
            />
          ))}
        </div>
      </div>

      <div className="table-card">
        <h2>All metrics</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Model</th><th>Precision</th><th>95% CI</th><th>Hit rate</th>
                <th>nDCG</th><th>Jobs returned</th><th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ id, name, values: m }) => (
                <tr key={id}>
                  <td>{name}</td>
                  <td>{percent(m.p5)}</td>
                  <td>{percent(m.p5_ci95[0])} to {percent(m.p5_ci95[1])}</td>
                  <td>{percent(m.hit5)}</td>
                  <td>{percent(m.ndcg5)}</td>
                  <td>{m.returned.toFixed(2)}</td>
                  <td>{m.latency_ms.toFixed(1)} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note method">
          O*NET {run.config.onet_version}. Each simulated user has {run.config.query_skills} skills
          from one occupation, which is hidden from the results. Metrics use the top {run.config.top_jobs} recommended
          jobs. {scope.occupations} occupations, {scope.clusters} clusters, {scope.skills.toLocaleString()} skills. Commit {run.git.commit}
          {run.git.uncommitted_changes ? " with uncommitted changes" : ""}.
        </p>
      </div>
    </section>
  );
}
