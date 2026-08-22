import pytest

from sync.models import (
    AccionRemediacion,
    Sincronizacion,
)
from sync.services import (
    crear_sincronizacion,
    ejecutar_remediacion,
)


@pytest.mark.django_db
def test_retry_job_sobre_rejected_es_exitoso():
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.REJECTED
    sincronizacion.finalizado_at = sincronizacion.iniciado_at

    sincronizacion.save(
        update_fields=[
            "estado",
            "finalizado_at",
        ]
    )

    accion = ejecutar_remediacion(
        sincronizacion=sincronizacion,
        accion_ejecutada="RETRY_JOB",
        ejecutado_por="pytest",
        notas="Reintento manual",
    )

    sincronizacion.refresh_from_db()

    assert sincronizacion.estado == Sincronizacion.Estado.PENDING
    assert sincronizacion.finalizado_at is None

    assert accion.resultado == AccionRemediacion.Resultado.SUCCESS
    assert accion.accion_ejecutada == "RETRY_JOB"
    assert accion.ejecutado_por == "pytest"
    assert accion.notas == "Reintento manual"

    assert AccionRemediacion.objects.count() == 1


@pytest.mark.django_db
def test_force_skip_validation_sobre_rejected_es_exitoso():
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.REJECTED

    sincronizacion.save(
        update_fields=["estado"]
    )

    accion = ejecutar_remediacion(
        sincronizacion=sincronizacion,
        accion_ejecutada="FORCE_SKIP_VALIDATION",
        ejecutado_por="pytest",
        notas="Omitir validación manualmente",
    )

    sincronizacion.refresh_from_db()

    assert sincronizacion.estado == Sincronizacion.Estado.COMPLETED
    assert sincronizacion.finalizado_at is not None

    assert accion.resultado == AccionRemediacion.Resultado.SUCCESS
    assert accion.accion_ejecutada == "FORCE_SKIP_VALIDATION"
    assert accion.ejecutado_por == "pytest"

    assert AccionRemediacion.objects.count() == 1


@pytest.mark.django_db
def test_retry_job_sobre_estado_no_reintentable_falla():
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.COMPLETED

    sincronizacion.save(
        update_fields=["estado"]
    )

    with pytest.raises(
        ValueError,
        match="La sincronización no se encuentra en un estado reintentable.",
    ):
        ejecutar_remediacion(
            sincronizacion=sincronizacion,
            accion_ejecutada="RETRY_JOB",
            ejecutado_por="pytest",
            notas="Intento inválido",
        )

    sincronizacion.refresh_from_db()

    assert sincronizacion.estado == Sincronizacion.Estado.COMPLETED

    assert AccionRemediacion.objects.count() == 1

    accion = AccionRemediacion.objects.first()

    assert accion.resultado == AccionRemediacion.Resultado.FAILED
    assert accion.accion_ejecutada == "RETRY_JOB"


@pytest.mark.django_db
def test_force_skip_validation_sobre_estado_no_rejected_falla():
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.PENDING

    sincronizacion.save(
        update_fields=["estado"]
    )

    with pytest.raises(
        ValueError,
        match=(
            "Solo se puede omitir la validación "
            "de una sincronización rechazada."
        ),
    ):
        ejecutar_remediacion(
            sincronizacion=sincronizacion,
            accion_ejecutada="FORCE_SKIP_VALIDATION",
            ejecutado_por="pytest",
        )

    sincronizacion.refresh_from_db()

    assert sincronizacion.estado == Sincronizacion.Estado.PENDING

    assert AccionRemediacion.objects.count() == 1

    accion = AccionRemediacion.objects.first()

    assert accion.resultado == AccionRemediacion.Resultado.FAILED
    assert accion.accion_ejecutada == "FORCE_SKIP_VALIDATION"


@pytest.mark.django_db
def test_accion_remediacion_no_soportada_falla():
    sincronizacion = crear_sincronizacion(
        usuario_origen="pytest",
    )

    sincronizacion.estado = Sincronizacion.Estado.REJECTED

    sincronizacion.save(
        update_fields=["estado"]
    )

    with pytest.raises(
        ValueError,
        match="Acción de remediación no soportada.",
    ):
        ejecutar_remediacion(
            sincronizacion=sincronizacion,
            accion_ejecutada="ACCION_DESCONOCIDA",
            ejecutado_por="pytest",
            notas="Acción inválida",
        )

    assert AccionRemediacion.objects.count() == 1

    accion = AccionRemediacion.objects.first()

    assert accion.resultado == AccionRemediacion.Resultado.FAILED
    assert accion.accion_ejecutada == "ACCION_DESCONOCIDA"
    assert accion.ejecutado_por == "pytest"