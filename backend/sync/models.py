import uuid

from django.db import models
from django.db.models.functions import Now


class Sincronizacion(models.Model):

    class Estado(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    correlation_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    fecha_ejecucion = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDING)
    iniciado_at = models.DateTimeField(auto_now_add=True)
    finalizado_at = models.DateTimeField(null=True, blank=True)
    usuario_origen = models.CharField(max_length=100)

    class Meta:
        db_table = "sincronizaciones"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[
                        "pending",
                        "running",
                        "completed",
                        "failed",
                        "rejected",
                    ]
                ),
                name="sync_estado_valido",
            ),
        ]

        indexes = [
            models.Index(
                fields=["estado", "iniciado_at"],
                name="idx_sync_estado_inicio",
            ),
        ]

    def __str__(self):
        return f"{self.correlation_id} - {self.estado}"


class ArchivoProcesado(models.Model):

    class TipoArchivo(models.TextChoices):
        VENTAS = "ventas", "Ventas"
        INVENTARIO = "inventario", "Inventario"
        CLIENTES = "clientes", "Clientes"

    class Estado(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    id = models.BigAutoField(primary_key=True)
    sincronizacion = models.ForeignKey(Sincronizacion, on_delete=models.CASCADE, related_name="archivos_procesados")
    nombre_archivo = models.CharField(max_length=255)
    tipo_archivo = models.CharField(max_length=20, choices=TipoArchivo.choices)
    checksum = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=20, choices=Estado.choices)
    registros_totales = models.IntegerField(default=0, db_default=0)
    datos_payload = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "archivos_procesados"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    tipo_archivo__in=[
                        "ventas",
                        "inventario",
                        "clientes",
                    ]
                ),
                name="archivo_tipo_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[
                        "accepted",
                        "rejected",
                    ]
                ),
                name="archivo_estado_valido",
            ),
        ]

    def __str__(self):
        return f"{self.nombre_archivo} - {self.estado}"


class LogError(models.Model):

    class NivelError(models.TextChoices):
        WARNING = "WARNING", "Warning"
        ERROR = "ERROR", "Error"
        CRITICAL = "CRITICAL", "Critical"

    id = models.BigAutoField(primary_key=True)
    sincronizacion = models.ForeignKey(Sincronizacion, to_field="correlation_id", db_column="correlation_id", on_delete=models.CASCADE, related_name="logs_errores")
    servicio_responsable = models.CharField(max_length=100)
    nivel_error = models.CharField(max_length=10, choices=NivelError.choices)
    codigo_error = models.CharField(max_length=50)
    mensaje = models.TextField()
    stack_trace = models.TextField(null=True, blank=True)
    creado_at = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "logs_errores"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    nivel_error__in=[
                        "WARNING",
                        "ERROR",
                        "CRITICAL",
                    ]
                ),
                name="log_nivel_valido",
            ),
        ]

        indexes = [
            models.Index(
                fields=["nivel_error", "creado_at"],
                name="idx_log_nivel_fecha",
            ),
        ]

    def __str__(self):
        return f"{self.codigo_error} - {self.nivel_error}"


class AccionRemediacion(models.Model):

    class Resultado(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    sincronizacion = models.ForeignKey(Sincronizacion, on_delete=models.CASCADE, related_name="acciones_remediacion")
    accion_ejecutada = models.CharField(max_length=100)
    ejecutado_por = models.CharField(max_length=100)
    resultado = models.CharField(max_length=10, choices=Resultado.choices)
    notas = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "acciones_remediacion"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    resultado__in=[
                        "success",
                        "failed",
                    ]
                ),
                name="remediacion_resultado_valido",
            ),
        ]

    def __str__(self):
        return f"{self.accion_ejecutada} - {self.resultado}"