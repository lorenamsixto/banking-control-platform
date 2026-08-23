import { useEffect, useState } from "react";

import { api } from "../api/client";
import LogsPanel from "../components/LogsPanel";
import MetricCard from "../components/MetricCard";
import SincronizacionesTable from "../components/SincronizacionesTable";
import type { DashboardMetricas } from "../types";

export default function Dashboard() {
  const [metricas, setMetricas] =
    useState<DashboardMetricas | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    const cargarMetricas = async () => {
      try {
        const response =
          await api.get<DashboardMetricas>(
            "/dashboard/metricas/"
          );

        setMetricas(response.data);
      } catch (error) {
        console.error(
          "Error al cargar las métricas:",
          error
        );

        setError(
          "No fue posible cargar las métricas."
        );
      } finally {
        setLoading(false);
      }
    };

    cargarMetricas();
  }, []);

  if (loading) {
    return (
      <main className="dashboard-page">
        Cargando métricas...
      </main>
    );
  }

  if (error || !metricas) {
    return (
      <main className="dashboard-page">
        {error ??
          "No hay métricas disponibles."}
      </main>
    );
  }

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <span className="dashboard-eyebrow">
          Banking Control Platform
        </span>

        <h1>
          Dashboard de Control de Fallas
        </h1>

        <p>
          Monitoreo de sincronizaciones, archivos
          rechazados y errores operativos.
        </p>
      </header>

      <section className="metrics-grid">
        <MetricCard
          title="Sincronizaciones activas"
          value={
            metricas.sincronizaciones_activas
          }
          icon="pi pi-sync"
          variant="blue"
        />

        <MetricCard
          title="Sincronizaciones completadas"
          value={
            metricas.sincronizaciones_completadas
          }
          icon="pi pi-check-circle"
          variant="green"
        />

        <MetricCard
          title="Sincronizaciones fallidas"
          value={
            metricas.sincronizaciones_fallidas
          }
          icon="pi pi-times-circle"
          variant="red"
        />

        <MetricCard
          title="Archivos rechazados"
          value={
            metricas.archivos_rechazados
          }
          icon="pi pi-file"
          variant="purple"
        />
      </section>

      <SincronizacionesTable />

      <LogsPanel />

      <footer className="dashboard-footer">
        © 2026 Banking Control Platform.
        Todos los derechos reservados.
      </footer>
    </main>
  );
}