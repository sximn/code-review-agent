import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricGrid } from "@/components/dashboard/metric-grid";

describe("MetricGrid", () => {
  it("renders weekly metrics", () => {
    render(
      <MetricGrid
        metrics={{
          reviews: 7,
          issuesCaught: 3,
          averageReviewTimeMinutes: 2.75,
        }}
        isEmpty={false}
      />,
    );

    const region = screen.getByRole("region", {
      name: "Review metrics this week",
    });
    expect(within(region).getByText("7")).toBeInTheDocument();
    expect(within(region).getByText("3")).toBeInTheDocument();
    expect(within(region).getByText("2.75m")).toBeInTheDocument();
    expect(within(region).getByText("Completed reviews")).toBeInTheDocument();
  });

  it("renders empty-state placeholders", () => {
    render(
      <MetricGrid
        metrics={{
          reviews: null as unknown as number,
          issuesCaught: null as unknown as number,
          averageReviewTimeMinutes: null,
        }}
        isEmpty
      />,
    );

    expect(screen.getAllByText("—")).toHaveLength(3);
    expect(screen.getByText("Awaiting your first repo")).toBeInTheDocument();
    expect(screen.getByText("Insights will appear here")).toBeInTheDocument();
  });
});
