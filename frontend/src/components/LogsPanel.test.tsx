import type { ReactNode } from "react";

import {
  fireEvent,
  render,
  screen,
} from "@testing-library/react";

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import LogsPanel from "./LogsPanel";
import { api } from "../api/client";


vi.mock("../api/client", () => ({
  api: {
    get: vi.fn(),
  },
}));


vi.mock("primereact/virtualscroller", () => ({
  VirtualScroller: ({
    items,
    itemTemplate,
  }: {
    items: unknown[];
    itemTemplate: (
      item: unknown,
      options: { index: number }
    ) => ReactNode;
  }) => (
    <div data-testid="virtual-scroller">
      {items.map((item, index) => (
        <div key={index}>
          {itemTemplate(item, { index })}
        </div>
      ))}
    </div>
  ),
}));


const mockedApi = vi.mocked(api);


const logPrueba = {
  id: 1,
  correlation_id: "corr-log-1",
  servicio_responsable: "Data_Worker",
  nivel_error: "CRITICAL",
  codigo_error: "ERR_PROCESSING_FAILURE",
  mensaje: "Error inesperado de prueba",
  stack_trace:
    "Traceback: RuntimeError de prueba",
  creado_at: "2026-08-23T10:00:00Z",
};


describe("LogsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it(
    "muestra un log obtenido del backend",
    async () => {
      mockedApi.get.mockResolvedValueOnce({
        data: [logPrueba],
      });

      render(<LogsPanel />);

      expect(
        await screen.findByText(
          "ERR_PROCESSING_FAILURE"
        )
      ).toBeTruthy();

      expect(
        screen.getByText(
          "Error inesperado de prueba"
        )
      ).toBeTruthy();

      expect(
        screen.getByText("Data_Worker")
      ).toBeTruthy();
    }
  );

  it(
    "abre el detalle del stack trace",
    async () => {
      mockedApi.get.mockResolvedValueOnce({
        data: [logPrueba],
      });

      render(<LogsPanel />);

      const boton =
        await screen.findByRole(
          "button",
          {
            name: /ver stack trace/i,
          }
        );

      fireEvent.click(boton);

      expect(
        await screen.findByText(
          "Detalle del error"
        )
      ).toBeTruthy();

      expect(
        screen.getByText(
          /Traceback: RuntimeError de prueba/i
        )
      ).toBeTruthy();
    }
  );
});