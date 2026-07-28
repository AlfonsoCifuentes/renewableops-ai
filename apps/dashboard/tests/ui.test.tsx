import { render, screen } from "@testing-library/react";
import { Activity } from "lucide-react";
import { describe, expect, it } from "vitest";

import { Badge, KpiCard } from "@/components/ui";
import { formatCurrency, formatNumber, labelForCause } from "@/lib/format";

describe("dashboard primitives", () => {
  it("renders an accessible KPI definition control", () => {
    render(
      <KpiCard
        label="nMAE forecast"
        value="4,2%"
        context="Champion"
        trend={-1.2}
        icon={<Activity />}
        onInfo={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: "Definición de nMAE forecast" })).toBeEnabled();
    expect(screen.getByText("4,2%")).toBeInTheDocument();
  });

  it("renders semantic badges", () => {
    render(<Badge tone="success">passed</Badge>);
    expect(screen.getByText("passed")).toHaveClass("badge-success");
  });
});

describe("Spanish presentation formatters", () => {
  it("formats metrics without changing their value", () => {
    expect(formatNumber(1234.5)).toContain("1234");
    expect(formatCurrency(5400)).toContain("€");
    expect(labelForCause("soiling")).toBe("Suciedad progresiva");
  });
});
