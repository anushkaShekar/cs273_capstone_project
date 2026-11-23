// Skills the recommended jobs ask for that the user did not pick
export default function SkillsToLearn({ skills, jobCount }) {
  return (
    <section className="section">
      <h2>Skills to learn</h2>
      <p className="note">
        Based on the jobs listed here. Skills common in these jobs but less
        common elsewhere rank higher.
      </p>

      {skills.length === 0 ? (
        <p className="empty">You already have the skills these jobs ask for.</p>
      ) : (
        <ul className="learn-list">
          {skills.map((item) => (
            <li key={item.skill}>
              <span className="learn-skill">{item.skill}</span>
              <span className="learn-count">
                used by {item.jobs} of {jobCount} jobs
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
