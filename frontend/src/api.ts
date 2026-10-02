import type { EvaluationResult, Sample } from "./types";

/** Posts the raw document text. The backend owns parsing, so the UI never
 *  decides whether JSON is well-formed -- one code path, one set of messages. */
export async function evaluateReport(raw: string): Promise<EvaluationResult> {
  const response = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw }),
  });

  if (!response.ok) {
    throw new Error(`Checker service returned ${response.status}.`);
  }

  return (await response.json()) as EvaluationResult;
}

/** Demo reports, read from the fixture files on disk by the backend, so the UI
 *  and the test suite can never drift apart. */
export async function fetchSamples(): Promise<Sample[]> {
  const response = await fetch("/api/samples");
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as Sample[];
}
