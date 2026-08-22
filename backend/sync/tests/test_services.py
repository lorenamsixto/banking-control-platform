import pytest
from django.db import OperationalError

from unittest.mock import Mock, patch

from sync.models import ArchivoProcesado, Sincronizacion
from sync.services import (
     BaseDatosNoDisponibleError,
    buscar_archivo_por_checksum,
    crear_sincronizacion,
    ejecutar_con_reintentos_db,
    registrar_archivo,
)


@pytest.mark.django_db
def test_crear_sincronizacion():
    sincronizacion = crear_sincronizacion(
        usuario_origen="lorena"
    )

    assert sincronizacion.id is not None
    assert sincronizacion.correlation_id is not None
    assert sincronizacion.usuario_origen == "lorena"
    assert sincronizacion.estado == Sincronizacion.Estado.PENDING
    assert sincronizacion.finalizado_at is None


@pytest.mark.django_db
def test_registrar_archivo():
    sincronizacion = crear_sincronizacion(
        usuario_origen="lorena"
    )

    archivo = registrar_archivo(
        sincronizacion=sincronizacion,
        nombre_archivo="ventas_test.json",
        tipo_archivo="ventas",
        checksum="a" * 64,
        estado=ArchivoProcesado.Estado.ACCEPTED,
        registros_totales=2,
        datos_payload=[
            {"producto": "Laptop"},
            {"producto": "Mouse"},
        ],
    )

    assert archivo.id is not None
    assert archivo.sincronizacion == sincronizacion
    assert archivo.nombre_archivo == "ventas_test.json"
    assert archivo.tipo_archivo == "ventas"
    assert archivo.checksum == "a" * 64
    assert archivo.estado == ArchivoProcesado.Estado.ACCEPTED
    assert archivo.registros_totales == 2
    assert len(archivo.datos_payload) == 2


@pytest.mark.django_db
def test_buscar_archivo_por_checksum_existente():
    sincronizacion = crear_sincronizacion(
        usuario_origen="lorena"
    )

    archivo_creado = registrar_archivo(
        sincronizacion=sincronizacion,
        nombre_archivo="ventas_test.json",
        tipo_archivo="ventas",
        checksum="b" * 64,
        estado=ArchivoProcesado.Estado.ACCEPTED,
        registros_totales=1,
        datos_payload=[
            {"producto": "Laptop"},
        ],
    )

    resultado = buscar_archivo_por_checksum(
        "b" * 64
    )

    assert resultado is not None
    assert resultado.id == archivo_creado.id
    assert resultado.checksum == "b" * 64


@pytest.mark.django_db
def test_buscar_archivo_por_checksum_inexistente():
    resultado = buscar_archivo_por_checksum(
        "c" * 64
    )

    assert resultado is None


@pytest.mark.django_db
def test_reintentos_db_operacion_exitosa():
    operacion = Mock(return_value="resultado_correcto")

    resultado = ejecutar_con_reintentos_db(
        operacion,
        max_intentos=4,
        base_delay=0.5,
    )

    assert resultado == "resultado_correcto"
    assert operacion.call_count == 1

@pytest.mark.django_db
@patch("sync.services.time.sleep")
@patch("sync.services.random.uniform", return_value=0.2)
def test_reintentos_db_recuperacion(
    mock_random,
    mock_sleep,
):
    operacion = Mock(
        side_effect=[
            OperationalError("DB caída"),
            OperationalError("DB caída"),
            "resultado_correcto",
        ]
    )

    resultado = ejecutar_con_reintentos_db(
        operacion,
        max_intentos=4,
        base_delay=0.5,
    )

    assert resultado == "resultado_correcto"
    assert operacion.call_count == 3
    assert mock_sleep.call_count == 2

    mock_sleep.assert_any_call(0.7)
    mock_sleep.assert_any_call(1.2)


@pytest.mark.django_db
@patch("sync.services.time.sleep")
@patch("sync.services.random.uniform", return_value=0.1)
def test_reintentos_db_agotados(
    mock_random,
    mock_sleep,
):
    operacion = Mock(
        side_effect=OperationalError(
            "PostgreSQL no disponible"
        )
    )

    with pytest.raises(
        BaseDatosNoDisponibleError,
        match="La base de datos no está disponible.",
    ):
        ejecutar_con_reintentos_db(
            operacion,
            max_intentos=4,
            base_delay=0.5,
        )

    assert operacion.call_count == 4
    assert mock_sleep.call_count == 3


@pytest.mark.django_db
@patch("sync.services.time.sleep")
@patch("sync.services.random.uniform", return_value=0.0)
def test_backoff_es_exponencial(
    mock_random,
    mock_sleep,
):
    operacion = Mock(
        side_effect=OperationalError("DB caída")
    )

    with pytest.raises(BaseDatosNoDisponibleError):
        ejecutar_con_reintentos_db(
            operacion,
            max_intentos=4,
            base_delay=0.5,
        )

    tiempos = [
        llamada.args[0]
        for llamada in mock_sleep.call_args_list
    ]

    assert tiempos == [
        0.5,
        1.0,
        2.0,
    ]