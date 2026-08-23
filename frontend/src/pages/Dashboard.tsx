import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { DashboardMetricas } from "../types";

export default function Dashboard() {
  const [metricas, setMetricas] =
    useState<DashboardMetricas | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cargarMetricas = async () => {
      try {
        const response = await api.get<DashboardMetricas>(
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
    return <p>Cargando métricas...</p>;
  }

  if (error) {
    return <p>{error}</p>;
  }

  if (!metricas) {
    return <p>No hay métricas disponibles.</p>;
  }

  return (
    <main>
      <h1>Dashboard de Control de Fallas</h1>

      <p>
        Sincronizaciones activas:{" "}
        {metricas.sincronizaciones_activas}
      </p>

      <p>
        Sincronizaciones completadas:{" "}
        {metricas.sincronizaciones_completadas}
      </p>

      <p>
        Sincronizaciones fallidas:{" "}
        {metricas.sincronizaciones_fallidas}
      </p>

      <p>
        Archivos rechazados:{" "}
        {metricas.archivos_rechazados}
      </p>
    </main>
  );
}