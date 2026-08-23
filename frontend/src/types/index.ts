export interface DashboardMetricas {
  sincronizaciones_activas: number;
  sincronizaciones_completadas: number;
  sincronizaciones_fallidas: number;
  archivos_rechazados: number;
}

export interface ArchivoProcesado {
  id: number;
  sincronizacion: string;
  nombre_archivo: string;
  tipo_archivo: string;
  checksum: string;
  estado: string;
  registros_totales: number;
  datos_payload: unknown;
}

export interface LogError {
  id: number;
  correlation_id: string;
  servicio_responsable: string;
  nivel_error: string;
  codigo_error: string;
  mensaje: string;
  stack_trace: string | null;
  creado_at: string;
}

export interface AccionRemediacion {
  id: number;
  sincronizacion: string;
  accion_ejecutada: string;
  ejecutado_por: string;
  resultado: string;
  notas: string | null;
}

export interface Sincronizacion {
  id: string;
  correlation_id: string;
  fecha_ejecucion: string;
  estado: string;
  iniciado_at: string;
  finalizado_at: string | null;
  usuario_origen: string;
  archivos_procesados: ArchivoProcesado[];
  logs_errores: LogError[];
  acciones_remediacion: AccionRemediacion[];
}