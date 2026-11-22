// Matching styles the user can choose from (id = model name the backend expects)
const MODELS = [
  {
    id: "one",
    name: "Exact skills",
    description: "I want jobs that use my exact skills.",
  },
  {
    id: "two",
    name: "Same field",
    description: "I want to explore jobs in my field.",
  },
  {
    id: "three",
    name: "Similar skills",
    description: "I'm open to jobs with similar skills.",
  },
];

// Three cards, one per matching style
export default function ModelPicker({ model, onChange }) {
  return (
    <fieldset className="models">
      <legend>What are you looking for?</legend>
      <div className="model-list">
        {MODELS.map((m) => (
          <label
            key={m.id}
            className={model === m.id ? "model active" : "model"}
          >
            <input
              type="radio"
              name="model"
              value={m.id}
              checked={model === m.id}
              onChange={() => onChange(m.id)}
            />
            <span className="model-name">{m.name}</span>
            <span className="model-desc">{m.description}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}