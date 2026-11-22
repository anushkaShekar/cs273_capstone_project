// The recommended jobs, best match first, with the user's matching skills
export default function JobResults({ results }) {
  return (
    <section className="section">
      <h2>Recommended jobs</h2>
      <p className="note">
        Listed from closest to least close match. The tags show which of your
        skills each job also uses.
      </p>
      <ol className="results">
        {results.map((job) => (
          <li key={job.occupation_title}>
            <span className="job-title">{job.occupation_title}</span>
            <div className="chips small">
              {job.matching_skills.map((s) => (
                <span className="chip" key={s}>{s}</span>
              ))}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}