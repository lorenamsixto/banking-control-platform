import { useEffect, useState } from "react";
import { InputText } from "primereact/inputtext";
import { Tag } from "primereact/tag";
import { Button } from "primereact/button";
import { Dialog } from "primereact/dialog";

import { api } from "../api/client";
import type { LogError } from "../types";

import { VirtualScroller } from "primereact/virtualscroller";

export default function LogsPanel() {
  const [logs, setLogs] = useState<LogError[]>([]);

  const [busqueda, setBusqueda] = useState("");
  const [busquedaDebounced, setBusquedaDebounced] =
    useState("");

  const [loading, setLoading] = useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [logSeleccionado, setLogSeleccionado] =
    useState<LogError | null>(null);

  const [dialogVisible, setDialogVisible] =
    useState(false);

  /*
   * Debounce manual de 300 ms.
   *
   * Evita realizar una petición al backend
   * por cada tecla que escribe el usuario.
   */
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setBusquedaDebounced(busqueda.trim());
    }, 300);

    return () => {
      window.clearTimeout(timer);
    };
  }, [busqueda]);

  /*
   * Cargar logs.
   *
   * Se ejecuta inicialmente y cada vez que
   * cambia la búsqueda después del debounce.
   */
  useEffect(() => {
    const cargarLogs = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.get<LogError[]>(
          "/logs/",
          {
            params: busquedaDebounced
              ? {
                  search: busquedaDebounced,
                }
              : {},
          }
        );

        setLogs(response.data);
      } catch (error) {
        console.error(
          "Error al cargar logs:",
          error
        );

        setError(
          "No fue posible cargar los logs."
        );
      } finally {
        setLoading(false);
      }
    };

    cargarLogs();
  }, [busquedaDebounced]);

  /*
   * Determina el color del Tag
   * según el nivel del error.
   */
  const obtenerSeveridad = (
    nivel: string
  ): "warning" | "danger" | "info" => {
    if (nivel === "WARNING") {
      return "warning";
    }

    if (
      nivel === "ERROR" ||
      nivel === "CRITICAL"
    ) {
      return "danger";
    }

    return "info";
  };

  /*
   * Abrir modal con el detalle
   * del log seleccionado.
   */
  const abrirDetalle = (log: LogError) => {
    setLogSeleccionado(log);
    setDialogVisible(true);
  };

  /*
   * Cerrar modal.
   */
  const cerrarDetalle = () => {
    setDialogVisible(false);
    setLogSeleccionado(null);
  };

  const logTemplate = (log: LogError) => (
    <article className="log-item">
      <div className="log-item-header">
        <strong className="log-code">
          {log.codigo_error}
        </strong>

        <Tag
          value={log.nivel_error}
          severity={obtenerSeveridad(log.nivel_error)}
        />
      </div>

      <p className="log-message">
        {log.mensaje}
      </p>

      <div className="log-meta">
        <span>
          <i className="pi pi-server" />
          {" "}
          {log.servicio_responsable}
        </span>

        <span>
          <i className="pi pi-clock" />
          {" "}
          {new Date(log.creado_at).toLocaleString("es-MX")}
        </span>
      </div>

      {log.stack_trace && (
        <div className="log-actions">
          <Button
            label="Ver stack trace"
            icon="pi pi-code"
            text
            size="small"
            onClick={() => abrirDetalle(log)}
          />
        </div>
      )}
    </article>
  );

  return (
    <section className="dashboard-section logs-section">
      {/* Encabezado */}
      <div className="section-header">
        <h2>
          <i className="pi pi-exclamation-circle section-icon section-icon-red" />

          Logs de errores
        </h2>

        <p>
          Consulta y seguimiento de errores registrados
          durante las sincronizaciones.
        </p>
      </div>

      {/* Buscador */}
      <div className="logs-search-container">
        <span className="p-input-icon-left logs-search-wrapper">
          <i className="pi pi-search" />

          <InputText
            value={busqueda}
            onChange={(event) =>
              setBusqueda(event.target.value)
            }
            placeholder="Buscar logs..."
            className="logs-search"
          />
        </span>
      </div>

      {/* Panel de logs */}
      <div className="logs-panel">
        {/* Cargando */}
        {loading && (
          <div className="empty-state">
            <i className="pi pi-spin pi-spinner" />

            <span>
              Cargando logs...
            </span>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="empty-state empty-state-error">
            <i className="pi pi-exclamation-triangle" />

            <span>
              {error}
            </span>
          </div>
        )}

        {/* Sin resultados */}
        {!loading &&
          !error &&
          logs.length === 0 && (
            <div className="empty-state">
              <i className="pi pi-inbox" />

              <span>
                No se encontraron logs.
              </span>
            </div>
          )}

        {/* Lista de logs */}
        {!loading && !error && logs.length > 0 && (
          <VirtualScroller
            items={logs}
            itemSize={160}
            itemTemplate={logTemplate}
            style={{
              width: "100%",
              height: "420px",
            }}
          />
        )}
      </div>

      {/* Modal Stack Trace */}
      <Dialog
        header="Detalle del error"
        visible={dialogVisible}
        modal
        closable
        closeOnEscape
        draggable={false}
        resizable={false}
        focusOnShow
        style={{
          width: "50rem",
          maxWidth: "95vw",
        }}
        onHide={cerrarDetalle}
      >
        {logSeleccionado && (
          <div className="stack-dialog-content">
            <div className="stack-dialog-meta">
              <div>
                <strong>Código:</strong>{" "}
                {logSeleccionado.codigo_error}
              </div>

              <div>
                <strong>Nivel:</strong>{" "}
                {logSeleccionado.nivel_error}
              </div>

              <div>
                <strong>Servicio:</strong>{" "}
                {logSeleccionado.servicio_responsable}
              </div>

              <div>
                <strong>Correlation ID:</strong>{" "}
                {logSeleccionado.correlation_id}
              </div>
            </div>

            <div
              className="stack-trace-container"
              tabIndex={0}
            >
              <pre>
                {logSeleccionado.stack_trace}
              </pre>
            </div>
          </div>
        )}
      </Dialog>
    </section>
  );
}