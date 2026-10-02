import type { Check } from "../types";

/** Evidence is shown verbatim as a supplied reference string. It is never
 *  fetched, linked, or described as verified. */
function evidenceCell(check: Check) {
  const blank = check.evidence === null || check.evidence.trim() === "";
  if (blank) {
    return <span className="evidence evidence--missing">missing</span>;
  }
  return <code className="evidence">{check.evidence}</code>;
}

export function CheckTable({ checks }: { checks: Check[] }) {
  if (checks.length === 0) {
    return <p className="empty">This report contains no checks.</p>;
  }

  return (
    <table className="checks">
      <caption>Evidence values are supplied reference strings. They are not fetched or verified.</caption>
      <thead>
        <tr>
          <th scope="col">ID</th>
          <th scope="col">Name</th>
          <th scope="col">Required</th>
          <th scope="col">Status</th>
          <th scope="col">Evidence</th>
        </tr>
      </thead>
      <tbody>
        {checks.map((check) => (
          <tr key={check.id}>
            <td><code>{check.id}</code></td>
            <td>{check.name}</td>
            <td>{check.required ? "required" : "optional"}</td>
            <td>
              <span className={`status status--${check.status}`}>{check.status}</span>
            </td>
            <td>{evidenceCell(check)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
