import { App } from "antd";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EvalReport } from "../api/conceptApi";

const report: EvalReport = {
  overall_score: 82.5,
  confidence: 0.6,
  passed: false,
  used_llm: false,
  blocking_issues: ["[security] Possible AWS secret in body"],
  recommendations: [],
  results: [
    { evaluator: "security", score: 50, findings: [{ severity: "error", message: "secret" }], blocking: true, used_llm: false },
    { evaluator: "documentation", score: 90, findings: [], blocking: false, used_llm: false },
    { evaluator: "governance", score: 95, findings: [], blocking: false, used_llm: false },
    { evaluator: "cost", score: 100, findings: [], blocking: false, used_llm: false },
    { evaluator: "performance", score: 100, findings: [], blocking: false, used_llm: false },
    { evaluator: "quality", score: 80, findings: [], blocking: false, used_llm: false },
  ],
};

vi.mock("../api/conceptApi", () => ({
  useEvaluateConcept: () => ({ isPending: false, mutate: vi.fn(), data: report }),
}));

import { EvaluatorPanel } from "../components/EvaluatorPanel";

describe("EvaluatorPanel", () => {
  it("renders all six evaluator rows and the blocking alert", () => {
    render(
      <App>
        <EvaluatorPanel workspaceId="w1" path="a.md" />
      </App>,
    );
    for (const name of ["security", "documentation", "governance", "cost", "performance", "quality"]) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
    expect(screen.getByText(/Blocking issues/i)).toBeInTheDocument();
    expect(screen.getByText(/Possible AWS secret/i)).toBeInTheDocument();
  });
});
