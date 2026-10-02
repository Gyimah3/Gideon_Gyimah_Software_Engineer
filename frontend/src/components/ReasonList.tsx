/** Renders blockers, warnings, or validation errors. Hidden when empty. */
export function ReasonList({
  title,
  reasons,
  tone,
}: {
  title: string;
  reasons: string[];
  tone: "blocker" | "warning" | "invalid";
}) {
  if (reasons.length === 0) {
    return null;
  }

  return (
    <section className={`reasons reasons--${tone}`}>
      <h2>
        {title} <span className="reasons__count">({reasons.length})</span>
      </h2>
      <ul>
        {reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </section>
  );
}
