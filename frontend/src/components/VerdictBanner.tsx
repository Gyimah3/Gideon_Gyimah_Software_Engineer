import type { Verdict } from "../types";

/** The one prominent overall result. */
export function VerdictBanner({ verdict }: { verdict: Verdict }) {
  return (
    <div className={`verdict verdict--${verdict.toLowerCase()}`} role="status" aria-live="polite">
      <span className="verdict__label">{verdict}</span>
      <span className="verdict__hint">
        {verdict === "READY"
          ? "Every required check passed and has evidence."
          : "This release cannot ship until the reasons below are resolved."}
      </span>
    </div>
  );
}
