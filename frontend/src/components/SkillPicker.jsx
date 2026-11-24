import { useState } from "react";

// Search box with a dropdown of skills, plus the chips for the skills picked so far
export default function SkillPicker({ allSkills, selected, onAdd, onRemove }) {
  const [query, setQuery] = useState("");   // text typed in the search box
  const [open, setOpen] = useState(false);  // is the dropdown showing?

  // Skills that match the search text and are not already picked
  const options = allSkills.filter(
    (s) => !selected.includes(s) && s.includes(query.toLowerCase())
  );

  function pick(skill) {
    onAdd(skill);
    setQuery("");
  }

  return (
    <>
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
          // Keeps the input focused while the user scrolls the list
          <ul className="options" onMouseDown={(e) => e.preventDefault()}>
            {options.length === 0 && <li className="none">No skills found</li>}
            {options.map((skill) => (
              <li key={skill} onMouseDown={() => pick(skill)}>
                {skill}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="chips">
        {selected.map((skill) => (
          <span className="chip" key={skill}>
            {skill}
            <button onClick={() => onRemove(skill)} aria-label={`Remove ${skill}`}>
              ×
            </button>
          </span>
        ))}
      </div>
    </>
  );
}
