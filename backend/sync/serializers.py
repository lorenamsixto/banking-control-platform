from rest_framework import serializers

from .models import AccionRemediacion, ArchivoProcesado, LogError, Sincronizacion


class ArchivoProcesadoSerializer(serializers.ModelSerializer):

    class Meta:
        model = ArchivoProcesado
        fields = [
            "id",
            "sincronizacion",
            "nombre_archivo",
            "tipo_archivo",
            "checksum",
            "estado",
            "registros_totales",
            "datos_payload",
        ]
        read_only_fields = ["id"]


class LogErrorSerializer(serializers.ModelSerializer):

    correlation_id = serializers.UUIDField(source="sincronizacion.correlation_id", read_only=True)

    class Meta:
        model = LogError
        fields = [
            "id",
            "correlation_id",
            "servicio_responsable",
            "nivel_error",
            "codigo_error",
            "mensaje",
            "stack_trace",
            "creado_at",
        ]
        read_only_fields = [
            "id",
            "correlation_id",
            "creado_at",
        ]


class AccionRemediacionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AccionRemediacion
        fields = [
            "id",
            "sincronizacion",
            "accion_ejecutada",
            "ejecutado_por",
            "resultado",
            "notas",
        ]
        read_only_fields = ["id"]


class SincronizacionSerializer(serializers.ModelSerializer):

    archivos_procesados = ArchivoProcesadoSerializer(many=True, read_only=True)
    logs_errores = LogErrorSerializer(many=True, read_only=True)
    acciones_remediacion = AccionRemediacionSerializer(many=True, read_only=True)

    class Meta:
        model = Sincronizacion
        fields = [
            "id",
            "correlation_id",
            "fecha_ejecucion",
            "estado",
            "iniciado_at",
            "finalizado_at",
            "usuario_origen",
            "archivos_procesados",
            "logs_errores",
            "acciones_remediacion",
        ]
        read_only_fields = [
            "id",
            "correlation_id",
            "iniciado_at",
            "finalizado_at",
            "archivos_procesados",
            "logs_errores",
            "acciones_remediacion",
        ]


class ProcesarArchivoSerializer(serializers.Serializer):

    archivo = serializers.FileField()
    tipo_archivo = serializers.ChoiceField(choices=ArchivoProcesado.TipoArchivo.choices)
    usuario_origen = serializers.CharField(max_length=100)


class RemediacionRequestSerializer(serializers.Serializer):

    sincronizacion_id = serializers.UUIDField()
    accion_ejecutada = serializers.ChoiceField(choices=["RETRY_JOB", "FORCE_SKIP_VALIDATION"])

    ejecutado_por = serializers.CharField(max_length=100)
    notas = serializers.CharField(required=False, allow_blank=True, allow_null=True)