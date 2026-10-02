/** Mirrors the /api/evaluate response. A drift from the backend is a compile error here. */

export type Status = "passed" | "failed" | "not_run";
export type Verdict = "READY" | "BLOCKED";

export interface Check {
  id: string;
  name: string;
  required: boolean;
  status: Status;
  evidence: string | null;
}

export interface EvaluationResult {
  verdict: Verdict;
  release: string | null;
  checks: Check[];
  blockers: string[];
  warnings: string[];
  validationErrors: string[];
}

/** A one-click demo report offered by the backend. */
export interface Sample {
  label: string;
  raw: string;
  verdict: Verdict;
}
