import { useEffect, useState } from "react";
import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import { Button } from "primereact/button";

import { api } from "../api/client";
import type { Sincronizacion } from "../types";

export default function SincronizacionesTable() {
  const [sincronizaciones, setSincronizaciones] =
    useState<Sincronizacion[]>([]);

  const [loading, setLoading] = useState(true);

  const cargarSincronizaciones = async () => {
    try {
      const response = await api.get<Sincronizacion[]>(
        "/sincronizaciones/"
      );

      setSincronizaciones(response.data);
    } catch (error) {
      console.error(
        "Error al cargar sincronizaciones:",
        error
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarSincronizaciones();
  }, []);

  const ejecutarRemediacion = async (
    sincronizacion: Sincronizacion,
    accion:
      | "RETRY_JOB"
      | "FORCE_SKIP_VALIDATION"
  ) => {
    try {
      await api.post("/remediaciones/", {
        sincronizacion_id: sincronizacion.id,
        accion_ejecutada: accion,
        ejecutado_por: "operador_dashboard",
        notas:
          "Acción ejecutada desde el dashboard",
      });

      await cargarSincronizaciones();
    } catch (error) {
      console.error(
        "Error al ejecutar remediación:",
        error
      );
    }
  };

  const estadoTemplate = (
    sincronizacion: Sincronizacion
  ) => (
    <span
      className={`status-badge status-${sincronizacion.estado}`}
    >
      {sincronizacion.estado}
    </span>
  );

  const fechaTemplate = (
    sincronizacion: Sincronizacion
  ) =>
    new Date(
      sincronizacion.iniciado_at
    ).toLocaleString("es-MX");

  const accionesTemplate = (
    sincronizacion: Sincronizacion
  ) => {
    const puedeReintentar =
      sincronizacion.estado === "failed" ||
      sincronizacion.estado === "rejected";

    const puedeOmitirValidacion =
      sincronizacion.estado === "rejected";

    if (
      !puedeReintentar &&
      !puedeOmitirValidacion
    ) {
      return (
        <span className="no-actions">
          —
        </span>
      );
    }

    return (
      <div className="sync-actions">
        {puedeReintentar && (
          <Button
            label="Reintentar"
            icon="pi pi-refresh"
            size="small"
            text
            onClick={() =>
              ejecutarRemediacion(
                sincronizacion,
                "RETRY_JOB"
              )
            }
          />
        )}

        {puedeOmitirValidacion && (
          <Button
            label="Omitir validación"
            icon="pi pi-check"
            size="small"
            text
            severity="warning"
            onClick={() =>
              ejecutarRemediacion(
                sincronizacion,
                "FORCE_SKIP_VALIDATION"
              )
            }
          />
        )}
      </div>
    );
  };

  return (
    <section className="dashboard-section">
      <div className="section-header">
        <h2>
          <i className="pi pi-clock section-icon section-icon-blue" />
          Sincronizaciones recientes
        </h2>

        <p>
          Seguimiento de ejecuciones y estados de procesamiento.
        </p>
      </div>

      <div className="table-panel">
        {!loading &&
        sincronizaciones.length === 0 ? (
          <>
            <div className="table-empty-header">
              <span>Correlation ID</span>
              <span>Usuario</span>
              <span>Estado</span>
              <span>Inicio</span>
              <span>Acciones</span>
            </div>

            <div className="empty-state">
              <i className="pi pi-inbox" />
              <span>
                No hay sincronizaciones recientes.
              </span>
            </div>
          </>
        ) : (
          <DataTable
            value={sincronizaciones}
            loading={loading}
            stripedRows
            responsiveLayout="scroll"
          >
            <Column
              field="correlation_id"
              header="Correlation ID"
            />

            <Column
              field="usuario_origen"
              header="Usuario"
            />

            <Column
              header="Estado"
              body={estadoTemplate}
            />

            <Column
              header="Inicio"
              body={fechaTemplate}
            />

            <Column
              header="Acciones"
              body={accionesTemplate}
            />
          </DataTable>
        )}
      </div>
    </section>
  );
}