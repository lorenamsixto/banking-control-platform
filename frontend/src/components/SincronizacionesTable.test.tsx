import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SincronizacionesTable from "./SincronizacionesTable";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe("SincronizacionesTable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("muestra las sincronizaciones obtenidas del backend", async () => {
    mockedApi.get.mockResolvedValueOnce({
      data: [
        {
          id: "1",
          correlation_id: "corr-123",
          usuario_origen: "usuario_prueba",
          estado: "completed",
          fecha_ejecucion: "2026-08-23",
          iniciado_at: "2026-08-23T10:00:00Z",
          finalizado_at: "2026-08-23T10:01:00Z",
        },
      ],
    });

    render(<SincronizacionesTable />);

    expect(
      await screen.findByText("corr-123")
    ).toBeTruthy();

    expect(
      screen.getByText("usuario_prueba")
    ).toBeTruthy();

    expect(
      screen.getByText("completed")
    ).toBeTruthy();
  });

  it("ejecuta RETRY_JOB para una sincronización failed", async () => {
    mockedApi.get
      .mockResolvedValueOnce({
        data: [
          {
            id: "sync-1",
            correlation_id: "corr-failed",
            usuario_origen: "tester",
            estado: "failed",
            fecha_ejecucion: "2026-08-23",
            iniciado_at: "2026-08-23T10:00:00Z",
            finalizado_at: "2026-08-23T10:01:00Z",
          },
        ],
      })
      .mockResolvedValueOnce({
        data: [
          {
            id: "sync-1",
            correlation_id: "corr-failed",
            usuario_origen: "tester",
            estado: "pending",
            fecha_ejecucion: "2026-08-23",
            iniciado_at: "2026-08-23T10:00:00Z",
            finalizado_at: null,
          },
        ],
      });

    mockedApi.post.mockResolvedValueOnce({
      data: {},
    });

    render(<SincronizacionesTable />);

    const boton = await screen.findByRole(
      "button",
      { name: /reintentar/i }
    );

    fireEvent.click(boton);

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith(
        "/remediaciones/",
        {
          sincronizacion_id: "sync-1",
          accion_ejecutada: "RETRY_JOB",
          ejecutado_por: "operador_dashboard",
          notas: "Acción ejecutada desde el dashboard",
        }
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText("pending")
      ).toBeTruthy();
    });
  });
});