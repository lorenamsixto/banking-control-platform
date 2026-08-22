from django.db import connection

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response

from django.db import models
from django.shortcuts import get_object_or_404

from .models import AccionRemediacion, ArchivoProcesado, LogError, Sincronizacion
from .serializers import (
    AccionRemediacionSerializer,
    ArchivoProcesadoSerializer,
    LogErrorSerializer,
    ProcesarArchivoSerializer,
    RemediacionRequestSerializer,
    SincronizacionSerializer,
)
from .services import (
    BaseDatosNoDisponibleError,
    PayloadInvalidoError,
    ProcesamientoInesperadoError,
    ejecutar_remediacion,
    procesar_archivo,
)

class SincronizacionListView(generics.ListAPIView):
    serializer_class = SincronizacionSerializer

    def get_queryset(self):
        return (
            Sincronizacion.objects
            .prefetch_related(
                "archivos_procesados",
                "logs_errores",
                "acciones_remediacion",
            )
            .order_by("-iniciado_at")
        )


class SincronizacionDetailView(generics.RetrieveAPIView):
    serializer_class = SincronizacionSerializer

    def get_queryset(self):
        return Sincronizacion.objects.prefetch_related(
            "archivos_procesados",
            "logs_errores",
            "acciones_remediacion",
        )


class LogErrorListView(generics.ListAPIView):
    serializer_class = LogErrorSerializer

    def get_queryset(self):
        queryset = (
            LogError.objects
            .select_related("sincronizacion")
            .order_by("-creado_at")
        )

        search = self.request.query_params.get("search")
        nivel = self.request.query_params.get("nivel")
        codigo = self.request.query_params.get("codigo")
        correlation_id = self.request.query_params.get("correlation_id")

        if search:
            queryset = queryset.filter(
                models.Q(mensaje__icontains=search)
                | models.Q(codigo_error__icontains=search)
                | models.Q(servicio_responsable__icontains=search)
            )

        if nivel:
            queryset = queryset.filter(
                nivel_error=nivel
            )

        if codigo:
            queryset = queryset.filter(
                codigo_error__icontains=codigo
            )

        if correlation_id:
            queryset = queryset.filter(
                sincronizacion__correlation_id=correlation_id
            )

        return queryset


class LogErrorDetailView(generics.RetrieveAPIView):
    serializer_class = LogErrorSerializer

    def get_queryset(self):
        return LogError.objects.select_related(
            "sincronizacion"
        )


class AccionRemediacionCreateView(APIView):

    def post(self, request):
        serializer = RemediacionRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        sincronizacion = get_object_or_404(
            Sincronizacion,
            id=serializer.validated_data["sincronizacion_id"],
        )

        try:
            accion = ejecutar_remediacion(
                sincronizacion=sincronizacion,
                accion_ejecutada=serializer.validated_data[
                    "accion_ejecutada"
                ],
                ejecutado_por=serializer.validated_data[
                    "ejecutado_por"
                ],
                notas=serializer.validated_data.get("notas"),
            )

        except ValueError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "codigo_error": "ERR_INVALID_REMEDIATION",
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            AccionRemediacionSerializer(accion).data,
            status=status.HTTP_201_CREATED,
        )


class ProcesarArchivoView(APIView):

    def post(self, request):
        serializer = ProcesarArchivoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        archivo = serializer.validated_data["archivo"]
        tipo_archivo = serializer.validated_data["tipo_archivo"]
        usuario_origen = serializer.validated_data["usuario_origen"]

        try:
            archivo_procesado, creado = procesar_archivo(
                archivo=archivo,
                tipo_archivo=tipo_archivo,
                usuario_origen=usuario_origen,
            )

        except PayloadInvalidoError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "codigo_error": "ERR_INVALID_PAYLOAD",
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        except BaseDatosNoDisponibleError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "codigo_error": "ERR_DATABASE_UNAVAILABLE",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except ProcesamientoInesperadoError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "codigo_error": "ERR_PROCESSING_FAILURE",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = ArchivoProcesadoSerializer(
            archivo_procesado
        )

        if creado:
            return Response(
                {
                    "idempotente": False,
                    "resultado": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "idempotente": True,
                "resultado": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class DashboardMetricasView(APIView):

    def get(self, request):
        sincronizaciones_activas = Sincronizacion.objects.filter(
            estado__in=[
                Sincronizacion.Estado.PENDING,
                Sincronizacion.Estado.RUNNING,
            ]
        ).count()

        sincronizaciones_completadas = Sincronizacion.objects.filter(
            estado=Sincronizacion.Estado.COMPLETED
        ).count()

        archivos_rechazados = ArchivoProcesado.objects.filter(
            estado=ArchivoProcesado.Estado.REJECTED
        ).count()

        sincronizaciones_fallidas = Sincronizacion.objects.filter(
            estado__in=[
                Sincronizacion.Estado.FAILED,
                Sincronizacion.Estado.REJECTED,
            ]
        ).count()

        return Response(
            {
                "sincronizaciones_activas": sincronizaciones_activas,
                "sincronizaciones_completadas": sincronizaciones_completadas,
                "sincronizaciones_fallidas": sincronizaciones_fallidas,
                "archivos_rechazados": archivos_rechazados,
            }
        )

class HealthCheckView(APIView):

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()

        return Response(
            {
                "status": "ok",
                "database": "ok",
            },
            status=status.HTTP_200_OK,
        )