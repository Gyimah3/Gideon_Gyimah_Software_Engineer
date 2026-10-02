import { useRef } from "react";

/** Both input methods feed the same textarea, so one submit path is exercised. */
export function InputPanel({
  raw,
  onRawChange,
  onSubmit,
  busy,
}: {
  raw: string;
  onRawChange: (value: string) => void;
  onSubmit: () => void;
  busy: boolean;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const empty = raw.trim() === "";

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    onRawChange(await file.text());
    // Reset so selecting the same file twice fires change again.
    event.target.value = "";
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && !empty && !busy) {
      onSubmit();
    }
  }

  return (
    <section className="panel">
      <div className="panel__head">
        <label className="panel__label" htmlFor="report-json">
          Release report JSON
        </label>
        <span className="panel__hint">
          <kbd>⌘</kbd>
          <kbd>↵</kbd> to check
        </span>
      </div>
      <textarea
        id="report-json"
        value={raw}
        spellCheck={false}
        onChange={(event) => onRawChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder='{"release": "demo-v1", "checks": [ ... ]}'
        rows={14}
      />
      <div className="panel__actions">
        <button
          type="button"
          className="primary"
          onClick={onSubmit}
          disabled={busy || empty}
          title={empty ? "Paste or load a report first" : undefined}
        >
          {busy ? "Checking…" : "Check release"}
        </button>
        <button type="button" onClick={() => fileInput.current?.click()} disabled={busy}>
          Load JSON file
        </button>
        <button type="button" onClick={() => onRawChange("")} disabled={busy || empty}>
          Clear
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          onChange={handleFile}
          hidden
        />
      </div>
    </section>
  );
}
