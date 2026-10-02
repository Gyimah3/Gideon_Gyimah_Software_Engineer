import type { Sample } from "../types";

/** One click fills the editor and runs the check. Keeps a live demo off the
 *  file-picker dialog. */
export function SampleBar({
  samples,
  onPick,
  busy,
}: {
  samples: Sample[];
  onPick: (sample: Sample) => void;
  busy: boolean;
}) {
  if (samples.length === 0) {
    return null;
  }

  return (
    <div className="samples">
      <span className="samples__label">Try</span>
      {samples.map((sample) => (
        <button
          key={sample.label}
          type="button"
          className="chip"
          onClick={() => onPick(sample)}
          disabled={busy}
          title={`Expects ${sample.verdict}`}
        >
          {sample.label}
          <span className={`chip__verdict chip__verdict--${sample.verdict.toLowerCase()}`}>
            {sample.verdict}
          </span>
        </button>
      ))}
    </div>
  );
}
