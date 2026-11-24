import { useState } from "react";

// How many skills to show before the user asks for the full list
const PREVIEW_COUNT = 25;

// One recommended job, with an expandable list of its skills
function JobCard({ job }) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const skills = job.job_skills || [];
  const visible = showAll ? skills : skills.slice(0, PREVIEW_COUNT);
  const panelId = `skills-${job.occupation_title.replace(/\W+/g, "-")}`;

  function toggle() {
    setExpanded(!expanded);
    setShowAll(false);
  }

  return (
    <li>
      <span className="job-title">{job.occupation_title}</span>
      <div className="chips small">
        {job.matching_skills.map((s) => (
          <span className="chip" key={s}>{s}</span>
        ))}
      </div>

      <button className="expand" aria-expanded={expanded} aria-controls={panelId} onClick={toggle}>
        <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
        {expanded ? "Hide job skills" : `View job skills (${skills.length})`}
      </button>

      {expanded && (
        <div className="job-skills" id={panelId}>
          <p className="job-skills-note">
            Showing {visible.length} of {skills.length}. Your skills are first and marked with ✓,
            followed by the skills fewest jobs use.
          </p>
          <ul
            className={showAll ? "job-skill-list scroll" : "job-skill-list"}
            tabIndex={showAll ? 0 : undefined}
            aria-label={`Skills for ${job.occupation_title}`}
          >
            {visible.map((item) => (
              <li key={item.skill} className={item.has ? "job-skill has" : "job-skill"}>
                {item.has && <span aria-label="You have this skill">✓ </span>}
                {item.skill}
              </li>
            ))}
          </ul>
          {skills.length > PREVIEW_COUNT && (
            <button className="show-all" onClick={() => setShowAll(!showAll)}>
              {showAll ? `Show top ${PREVIEW_COUNT}` : `Show all ${skills.length} skills`}
            </button>
          )}
        </div>
      )}
    </li>
  );
}

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
          <JobCard job={job} key={job.occupation_title} />
        ))}
      </ol>
    </section>
  );
}
