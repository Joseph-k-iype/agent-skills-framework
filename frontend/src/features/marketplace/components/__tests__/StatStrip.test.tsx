import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatStrip } from "../StatStrip";

describe("StatStrip", () => {
  it("renders uses, clones, versions+latest, and created/updated from a fixture", () => {
    render(
      <StatStrip
        uses={128}
        clones={7}
        versionCount={3}
        latestVersion={3}
        createdAt="2026-01-15T10:00:00Z"
        updatedAt="2026-06-20T10:00:00Z"
      />,
    );
    expect(screen.getByText("128")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    // versions count + latest label
    expect(screen.getByText(/uses/i)).toBeInTheDocument();
    expect(screen.getByText(/clones/i)).toBeInTheDocument();
    expect(screen.getByText(/versions/i)).toBeInTheDocument();
    expect(screen.getByText(/v3/)).toBeInTheDocument();
    // created + updated dates rendered (year visible)
    expect(screen.getAllByText(/2026/).length).toBeGreaterThan(0);
  });
});
