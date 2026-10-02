import { useCallback, useEffect, useState } from "react";

import { evaluateReport, fetchSamples } from "./api";
import { CheckTable } from "./components/CheckTable";
import { InputPanel } from "./components/InputPanel";
import { ReasonList } from "./components/ReasonList";
import { ResultSummary } from "./components/ResultSummary";
import { SampleBar } from "./components/SampleBar";
import { VerdictBanner } from "./components/VerdictBanner";
import type { EvaluationResult, Sample } from "./types";

export function App() {
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [transportError, setTransportError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [samples, setSamples] = useState<Sample[]>([]);

  useEffect(() => {
    void fetchSamples().then(setSamples);
  }, []);

  const check = useCallback(async (text: string) => {
    // Clearing both before the request is what makes a stale READY impossible:
    // the previous verdict is gone before the new one is requested.
    setResult(null);
    setTransportError(null);
    setBusy(true);
    try {
      setResult(await evaluateReport(text));
    } catch (error) {
      setTransportError(
        error instanceof Error ? error.message : "Could not reach the checker service.",
      );
    } finally {
      setBusy(false);
    }
  }, []);

  function pickSample(sample: Sample) {
    setRaw(sample.raw);
    void check(sample.raw);
  }

  return (
    <main>
      <header>
        <h1>Release evidence checker</h1>
        <p>
          Every required check must have passed and carry nonblank evidence for a release to be
          READY. Evidence is read as a reference string; it is never fetched.
        </p>
      </header>

      <SampleBar samples={samples} onPick={pickSample} busy={busy} />

      <InputPanel raw={raw} onRawChange={setRaw} onSubmit={() => void check(raw)} busy={busy} />

      {transportError && (
        <section className="reasons reasons--invalid">
          <h2>Could not check this report</h2>
          <ul>
            <li>{transportError}</li>
          </ul>
        </section>
      )}

      {result && (
        <section className="result">
          <VerdictBanner verdict={result.verdict} />
          <div className="result__meta">
            {result.release && (
              <p className="release">
                Release <strong>{result.release}</strong>
              </p>
            )}
            <ResultSummary result={result} />
          </div>
          <ReasonList title="Blocking reasons" reasons={result.blockers} tone="blocker" />
          <ReasonList title="Invalid data" reasons={result.validationErrors} tone="invalid" />
          <ReasonList title="Warnings" reasons={result.warnings} tone="warning" />
          {result.validationErrors.length === 0 && <CheckTable checks={result.checks} />}
        </section>
      )}
    </main>
  );
}
