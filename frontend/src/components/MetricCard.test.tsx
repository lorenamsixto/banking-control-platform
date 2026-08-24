import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MetricCard from "./MetricCard";

describe("MetricCard", () => {
  it("muestra el título y el valor", () => {
    render(
      <MetricCard
        title="Sincronizaciones activas"
        value={5}
        icon="pi pi-sync"
        variant="blue"
      />
    );

    expect(
      screen.getByText("Sincronizaciones activas")
    ).toBeTruthy();

    expect(screen.getByText("5")).toBeTruthy();
  });
});