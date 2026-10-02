import type { EvaluationResult } from "../types";

/** A countable one-line read of the result, for scanning before reading prose. */
export function ResultSummary({ result }: { result: EvaluationResult }) {
  const required = result.checks.filter((c) => c.required).length;
  const optional = result.checks.length - required;

  const parts = [
    `${required} required`,
    `${optional} optional`,
    `${result.blockers.length} blocking`,
    `${result.warnings.length} warning${result.warnings.length === 1 ? "" : "s"}`,
  ];

  const invalid = result.validationErrors.length;
  if (invalid > 0) {
    return (
      <p className="summary">
        {invalid} validation {invalid === 1 ? "error" : "errors"}
      </p>
    );
  }

  return <p className="summary">{parts.join(" · ")}</p>;
}
