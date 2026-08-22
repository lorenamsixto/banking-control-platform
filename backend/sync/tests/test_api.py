import json
import pytest

from django.db import OperationalError
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from rest_framework.test import APIClient

from sync.cpu_tasks import (
    calcular_checksum_bytes,
    parsear_payload_bytes,
)
from sync.models import (
    ArchivoProcesado,
    LogError,
    Sincronizacion,
)
from sync.services import (
    BaseDatosNoDisponibleError,
    crear_sincronizacion,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def configurar_servicios_para_tests_api(monkeypatch):
    """
    Configuración especial para los tests de API.

    - Ejecutamos directamente las tareas CPU para evitar abrir
      procesos reales con ProcessPoolExecutor durante pytest.
    - Evitamos close_old_connections(), porque pytest-django
      administra la conexión de la base de datos de pruebas.

    Los ProcessPool y los retries reales de PostgreSQL se prueban
    por separado.
    """

    monkeypatch.setattr(
        "sync.services.ejecutar_checksum_cpu",
        calcular_checksum_bytes,
    )

    monkeypatch.setattr(
        "sync.services.ejecutar_parseo_cpu",
        parsear_payload_bytes,
    )

    monkeypatch.setattr(
        "sync.services.close_old_connections",
        lambda: None,
    )


@pytest.fixture
def archivo_valido():
    contenido = json.dumps(
        [
            {
                "producto": "Laptop",
                "cantidad": 2,
                "total": 35000,
            },
            {
                "producto": "Monitor",
                "cantidad": 3,
                "total": 15000,
            },
        ]
    ).encode("utf-8")

    return SimpleUploadedFile(
        "ventas_api_test.json",
        contenido,
        content_type="application/json",
    )


@pytest.mark.django_db
def test_procesar_archivo_valido(
    api_client,
    archivo_valido,
):
    response = api_client.post(
        "/api/procesar/",
        {
            "archivo": archivo_valido,
            "tipo_archivo": "ventas",
            "usuario_origen": "pytest",
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["idempotente"] is False

    resultado = response.data["resultado"]

    assert resultado["nombre_archivo"] == "ventas_api_test.json"
    assert resultado["tipo_archivo"] == "ventas"
    assert resultado["estado"] == "accepted"
    assert resultado["registros_totales"] == 2

    assert Sincronizacion.objects.count() == 1
    assert ArchivoProcesado.objects.count() == 1

    sincronizacion = Sincronizacion.objects.first()
    archivo = ArchivoProcesado.objects.first()

    assert sincronizacion.estado == Sincronizacion.Estado.COMPLETED
    assert sincronizacion.finalizado_at is not None

    assert archivo.estado == ArchivoProcesado.Estado.ACCEPTED
    assert archivo.registros_totales == 2
    assert len(archivo.datos_payload) == 2


@pytest.mark.django_db
def test_procesar_mismo_archivo_es_idempotente(
    api_client,
):
    contenido = json.dumps(
        [
            {
                "producto": "Teclado",
                "cantidad": 5,
                "total": 5000,
            }
        ]
    ).encode("utf-8")

    def crear_archivo():
        return SimpleUploadedFile(
            "ventas_idempotencia.json",
            contenido,
            content_type="application/json",
        )

    primera = api_client.post(
        "/api/procesar/",
        {
            "archivo": crear_archivo(),
            "tipo_archivo": "ventas",
            "usuario_origen": "pytest",
        },
        format="multipart",
    )

    segunda = api_client.post(
        "/api/procesar/",
        {
            "archivo": crear_archivo(),
            "tipo_archivo": "ventas",
            "usuario_origen": "pytest",
        },
        format="multipart",
    )

    assert primera.status_code == 201
    assert segunda.status_code == 200

    assert primera.data["idempotente"] is False
    assert segunda.data["idempotente"] is True

    assert (
        primera.data["resultado"]["id"]
        == segunda.data["resultado"]["id"]
    )

    assert (
        primera.data["resultado"]["checksum"]
        == segunda.data["resultado"]["checksum"]
    )

    assert (
        primera.data["resultado"]["sincronizacion"]
        == segunda.data["resultado"]["sincronizacion"]
    )

    assert ArchivoProcesado.objects.count() == 1
    assert Sincronizacion.objects.count() == 1


@pytest.mark.django_db
def test_payload_corrupto_genera_422_y_log(
    api_client,
):
    archivo = SimpleUploadedFile(
        "ventas_corrupto.json",
        b'[{"producto": "Laptop", "cantidad": }]',
        content_type="application/json",
    )

    response = api_client.post(
        "/api/procesar/",
        {
            "archivo": archivo,
            "tipo_archivo": "ventas",
            "usuario_origen": "pytest",
        },
        format="multipart",
    )

    assert response.status_code == 422

    assert (
        response.data["codigo_error"]
        == "ERR_INVALID_PAYLOAD"
    )

    assert (
        response.data["detail"]
        == "El archivo contiene JSON inválido."
    )

    assert Sincronizacion.objects.count() == 1
    assert ArchivoProcesado.objects.count() == 1
    assert LogError.objects.count() == 1

    sincronizacion = Sincronizacion.objects.first()
    archivo_procesado = ArchivoProcesado.objects.first()
    log = LogError.objects.first()

    assert (
        sincronizacion.estado
        == Sincronizacion.Estado.REJECTED
    )

    assert sincronizacion.finalizado_at is not None

    assert (
        archivo_procesado.estado
        == ArchivoProcesado.Estado.REJECTED
    )

    assert archivo_procesado.registros_totales == 0
    assert archivo_procesado.datos_payload is None

    assert (
        log.codigo_error
        == "ERR_INVALID_PAYLOAD"
    )

    assert (
        log.nivel_error
        == LogError.NivelError.ERROR
    )

    assert (
        log.servicio_responsable
        == "Validation_Engine"
    )

    assert (
        log.mensaje
        == "El archivo contiene JSON inválido."
    )

    assert (
        log.sincronizacion.correlation_id
        == sincronizacion.correlation_id
    )


@pytest.mark.django_db
@patch("sync.views.procesar_archivo")
def test_base_datos_no_disponible_devuelve_503(
    mock_procesar,
    api_client,
    archivo_valido,
):
    mock_procesar.side_effect = BaseDatosNoDisponibleError(
        "La base de datos no está disponible."
    )

    response = api_client.post(
        "/api/procesar/",
        {
            "archivo": archivo_valido,
            "tipo_archivo": "ventas",
            "usuario_origen": "pytest",
        },
        format="multipart",
    )

    assert response.status_code == 503

    assert (
        response.data["codigo_error"]
        == "ERR_DATABASE_UNAVAILABLE"
    )

    assert (
        response.data["detail"]
        == "La base de datos no está disponible."
    )


@pytest.mark.django_db
def test_listar_sincronizaciones(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.COMPLETED
    sincronizacion.finalizado_at = sincronizacion.iniciado_at

    sincronizacion.save(
        update_fields=[
            "estado",
            "finalizado_at",
        ]
    )

    response = api_client.get(
        "/api/sincronizaciones/"
    )

    assert response.status_code == 200
    assert len(response.data) == 1

    resultado = response.data[0]

    assert resultado["id"] == str(sincronizacion.id)

    assert (
        resultado["correlation_id"]
        == str(sincronizacion.correlation_id)
    )

    assert resultado["usuario_origen"] == "pytest"
    assert resultado["estado"] == "completed"

    assert resultado["archivos_procesados"] == []
    assert resultado["logs_errores"] == []
    assert resultado["acciones_remediacion"] == []


@pytest.mark.django_db
def test_detalle_sincronizacion(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    response = api_client.get(
        f"/api/sincronizaciones/{sincronizacion.id}/"
    )

    assert response.status_code == 200
    assert response.data["id"] == str(sincronizacion.id)
    assert (
        response.data["correlation_id"]
        == str(sincronizacion.correlation_id)
    )
    assert response.data["usuario_origen"] == "pytest"


@pytest.mark.django_db
def test_listar_logs(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Validation_Engine",
        nivel_error=LogError.NivelError.ERROR,
        codigo_error="ERR_TEST",
        mensaje="Error de prueba",
    )

    response = api_client.get(
        "/api/logs/"
    )

    assert response.status_code == 200
    assert len(response.data) == 1

    assert response.data[0]["codigo_error"] == "ERR_TEST"
    assert response.data[0]["nivel_error"] == "ERROR"


@pytest.mark.django_db
def test_buscar_logs_por_search(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Validation_Engine",
        nivel_error=LogError.NivelError.ERROR,
        codigo_error="ERR_INVALID_PAYLOAD",
        mensaje="El archivo contiene JSON inválido.",
    )

    LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Data_Worker",
        nivel_error=LogError.NivelError.CRITICAL,
        codigo_error="ERR_DB_TIMEOUT",
        mensaje="Timeout de base de datos",
    )

    response = api_client.get(
        "/api/logs/?search=payload"
    )

    assert response.status_code == 200
    assert len(response.data) == 1
    assert (
        response.data[0]["codigo_error"]
        == "ERR_INVALID_PAYLOAD"
    )


@pytest.mark.django_db
def test_filtrar_logs_por_nivel(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Validation_Engine",
        nivel_error=LogError.NivelError.ERROR,
        codigo_error="ERR_TEST_1",
        mensaje="Error normal",
    )

    LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Data_Worker",
        nivel_error=LogError.NivelError.CRITICAL,
        codigo_error="ERR_TEST_2",
        mensaje="Error crítico",
    )

    response = api_client.get(
        "/api/logs/?nivel=CRITICAL"
    )

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["nivel_error"] == "CRITICAL"



@pytest.mark.django_db
def test_filtrar_logs_por_codigo(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Validation_Engine",
        nivel_error=LogError.NivelError.ERROR,
        codigo_error="ERR_CHECKSUM_MISMATCH",
        mensaje="Checksum inválido",
    )

    response = api_client.get(
        "/api/logs/?codigo=CHECKSUM"
    )

    assert response.status_code == 200
    assert len(response.data) == 1
    assert (
        response.data[0]["codigo_error"]
        == "ERR_CHECKSUM_MISMATCH"
    )



@pytest.mark.django_db
def test_filtrar_logs_por_correlation_id(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    otra_sincronizacion = crear_sincronizacion(
        usuario_origen="otro",
    )

    LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Validation_Engine",
        nivel_error=LogError.NivelError.ERROR,
        codigo_error="ERR_TEST_1",
        mensaje="Primer error",
    )

    LogError.objects.create(
        sincronizacion=otra_sincronizacion,
        servicio_responsable="Data_Worker",
        nivel_error=LogError.NivelError.ERROR,
        codigo_error="ERR_TEST_2",
        mensaje="Segundo error",
    )

    response = api_client.get(
        f"/api/logs/?correlation_id={sincronizacion.correlation_id}"
    )

    assert response.status_code == 200
    assert len(response.data) == 1

    assert (
        response.data[0]["correlation_id"]
        == str(sincronizacion.correlation_id)
    )



@pytest.mark.django_db
def test_detalle_log(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    log = LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable="Data_Worker",
        nivel_error=LogError.NivelError.CRITICAL,
        codigo_error="ERR_TEST",
        mensaje="Error crítico",
        stack_trace="Traceback de prueba",
    )

    response = api_client.get(
        f"/api/logs/{log.id}/"
    )

    assert response.status_code == 200
    assert response.data["id"] == log.id
    assert response.data["stack_trace"] == "Traceback de prueba"



@pytest.mark.django_db
def test_metricas_dashboard(
    api_client,
):
    crear_sincronizacion(
        usuario_origen="pending",
    )

    running = crear_sincronizacion(
        usuario_origen="running",
    )
    running.estado = Sincronizacion.Estado.RUNNING
    running.save(update_fields=["estado"])

    completed = crear_sincronizacion(
        usuario_origen="completed",
    )
    completed.estado = Sincronizacion.Estado.COMPLETED
    completed.save(update_fields=["estado"])

    rejected = crear_sincronizacion(
        usuario_origen="rejected",
    )
    rejected.estado = Sincronizacion.Estado.REJECTED
    rejected.save(update_fields=["estado"])

    ArchivoProcesado.objects.create(
        sincronizacion=rejected,
        nombre_archivo="rechazado.json",
        tipo_archivo="ventas",
        checksum="f" * 64,
        estado=ArchivoProcesado.Estado.REJECTED,
    )

    response = api_client.get(
        "/api/dashboard/metricas/"
    )

    assert response.status_code == 200

    assert response.data["sincronizaciones_activas"] == 2
    assert response.data["sincronizaciones_completadas"] == 1
    assert response.data["sincronizaciones_fallidas"] == 1
    assert response.data["archivos_rechazados"] == 1


@pytest.mark.django_db
def test_endpoint_remediacion_exitosa(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.REJECTED
    sincronizacion.save(
        update_fields=["estado"]
    )

    response = api_client.post(
        "/api/remediaciones/",
        {
            "sincronizacion_id": str(sincronizacion.id),
            "accion_ejecutada": "RETRY_JOB",
            "ejecutado_por": "pytest",
            "notas": "Reintento desde test",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["resultado"] == "success"

    sincronizacion.refresh_from_db()

    assert sincronizacion.estado == Sincronizacion.Estado.PENDING


@pytest.mark.django_db
def test_endpoint_remediacion_invalida_devuelve_409(
    api_client,
):
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.COMPLETED
    sincronizacion.save(
        update_fields=["estado"]
    )

    response = api_client.post(
        "/api/remediaciones/",
        {
            "sincronizacion_id": str(sincronizacion.id),
            "accion_ejecutada": "RETRY_JOB",
            "ejecutado_por": "pytest",
        },
        format="json",
    )

    assert response.status_code == 409

    assert (
        response.data["codigo_error"]
        == "ERR_INVALID_REMEDIATION"
    )



@pytest.mark.django_db
@patch("sync.views.Sincronizacion.objects")
def test_operational_error_global_devuelve_503(
    mock_objects,
    api_client,
):
    mock_objects.prefetch_related.side_effect = OperationalError(
        "PostgreSQL no disponible"
    )

    response = api_client.get(
        "/api/sincronizaciones/"
    )

    assert response.status_code == 503

    assert (
        response.data["codigo_error"]
        == "ERR_DATABASE_UNAVAILABLE"
    )

    assert (
        response.data["detail"]
        == "La base de datos no está disponible."
    )


@pytest.mark.django_db
def test_health_check_ok(
    api_client,
):
    response = api_client.get(
        "/api/health/"
    )

    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert response.data["database"] == "ok"


@pytest.mark.django_db
@patch("sync.views.connection.cursor")
def test_health_check_db_no_disponible(
    mock_cursor,
    api_client,
):
    mock_cursor.side_effect = OperationalError(
        "PostgreSQL no disponible"
    )

    response = api_client.get(
        "/api/health/"
    )

    assert response.status_code == 503

    assert (
        response.data["codigo_error"]
        == "ERR_DATABASE_UNAVAILABLE"
    )