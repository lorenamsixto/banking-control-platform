import random
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

from django.db import (
    IntegrityError,
    OperationalError,
    close_old_connections,
    transaction,
)
from django.utils import timezone

from .cpu_tasks import (
    PayloadCPUError,
    calcular_checksum_bytes,
    parsear_payload_bytes,
)
from .models import (
    AccionRemediacion,
    ArchivoProcesado,
    LogError,
    Sincronizacion,
)


CPU_EXECUTOR = ProcessPoolExecutor(max_workers=2)


class PayloadInvalidoError(Exception):
    """El archivo recibido contiene un payload inválido."""

    pass


class BaseDatosNoDisponibleError(Exception):
    """PostgreSQL no está disponible después de los reintentos."""

    pass


class ProcesamientoInesperadoError(Exception):
    """Ocurrió una falla inesperada durante el procesamiento."""

    pass


def leer_archivo(archivo):
    contenido = archivo.read()
    archivo.seek(0)

    return contenido


def ejecutar_checksum_cpu(contenido):
    future = CPU_EXECUTOR.submit(
        calcular_checksum_bytes,
        contenido,
    )

    return future.result()


def ejecutar_parseo_cpu(contenido):
    future = CPU_EXECUTOR.submit(
        parsear_payload_bytes,
        contenido,
    )

    return future.result()


def buscar_archivo_por_checksum(checksum):
    return (
        ArchivoProcesado.objects
        .select_related("sincronizacion")
        .filter(checksum=checksum)
        .first()
    )


def crear_sincronizacion(usuario_origen):
    return Sincronizacion.objects.create(
        fecha_ejecucion=timezone.localdate(),
        estado=Sincronizacion.Estado.PENDING,
        usuario_origen=usuario_origen,
    )


def registrar_archivo(
    sincronizacion,
    nombre_archivo,
    tipo_archivo,
    checksum,
    estado,
    registros_totales=0,
    datos_payload=None,
):
    return ArchivoProcesado.objects.create(
        sincronizacion=sincronizacion,
        nombre_archivo=nombre_archivo,
        tipo_archivo=tipo_archivo,
        checksum=checksum,
        estado=estado,
        registros_totales=registros_totales,
        datos_payload=datos_payload,
    )


def registrar_error(
    sincronizacion,
    servicio_responsable,
    nivel_error,
    codigo_error,
    mensaje,
    stack_trace=None,
):
    return LogError.objects.create(
        sincronizacion=sincronizacion,
        servicio_responsable=servicio_responsable,
        nivel_error=nivel_error,
        codigo_error=codigo_error,
        mensaje=mensaje,
        stack_trace=stack_trace,
    )


def registrar_fallo_inesperado(
    sincronizacion,
    exc,
):
    stack_trace = "".join(
        traceback.format_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )
    )

    with transaction.atomic():
        registrar_error(
            sincronizacion=sincronizacion,
            servicio_responsable="Data_Worker",
            nivel_error=LogError.NivelError.CRITICAL,
            codigo_error="ERR_PROCESSING_FAILURE",
            mensaje=(
                "Ocurrió un error inesperado "
                "durante el procesamiento."
            ),
            stack_trace=stack_trace,
        )

        sincronizacion.estado = Sincronizacion.Estado.FAILED
        sincronizacion.finalizado_at = timezone.now()

        sincronizacion.save(
            update_fields=[
                "estado",
                "finalizado_at",
            ]
        )


def ejecutar_con_reintentos_db(
    operacion,
    max_intentos=4,
    base_delay=0.5,
):
    for intento in range(max_intentos):
        try:
            close_old_connections()

            return operacion()

        except OperationalError as exc:
            close_old_connections()

            if intento == max_intentos - 1:
                raise BaseDatosNoDisponibleError(
                    "La base de datos no está disponible."
                ) from exc

            delay_exponencial = base_delay * (2 ** intento)
            jitter = random.uniform(0, base_delay)

            time.sleep(
                delay_exponencial + jitter
            )


def _guardar_resultado_procesamiento(
    sincronizacion,
    archivo,
    tipo_archivo,
    checksum,
    payload=None,
    error_payload=None,
):
    with transaction.atomic():

        sincronizacion.estado = Sincronizacion.Estado.RUNNING

        sincronizacion.save(
            update_fields=["estado"]
        )

        if error_payload is not None:
            archivo_procesado = registrar_archivo(
                sincronizacion=sincronizacion,
                nombre_archivo=archivo.name,
                tipo_archivo=tipo_archivo,
                checksum=checksum,
                estado=ArchivoProcesado.Estado.REJECTED,
                registros_totales=0,
                datos_payload=None,
            )

            registrar_error(
                sincronizacion=sincronizacion,
                servicio_responsable="Validation_Engine",
                nivel_error=LogError.NivelError.ERROR,
                codigo_error="ERR_INVALID_PAYLOAD",
                mensaje=str(error_payload),
            )

            sincronizacion.estado = (
                Sincronizacion.Estado.REJECTED
            )

        else:
            archivo_procesado = registrar_archivo(
                sincronizacion=sincronizacion,
                nombre_archivo=archivo.name,
                tipo_archivo=tipo_archivo,
                checksum=checksum,
                estado=ArchivoProcesado.Estado.ACCEPTED,
                registros_totales=len(payload),
                datos_payload=payload,
            )

            sincronizacion.estado = (
                Sincronizacion.Estado.COMPLETED
            )

        sincronizacion.finalizado_at = timezone.now()

        sincronizacion.save(
            update_fields=[
                "estado",
                "finalizado_at",
            ]
        )

        return archivo_procesado


def procesar_archivo(
    archivo,
    tipo_archivo,
    usuario_origen,
):
    contenido = leer_archivo(archivo)

    checksum = ejecutar_checksum_cpu(
        contenido
    )

    archivo_existente = ejecutar_con_reintentos_db(
        lambda: buscar_archivo_por_checksum(
            checksum
        )
    )

    if archivo_existente:
        return archivo_existente, False

    try:
        payload = ejecutar_parseo_cpu(
            contenido
        )
        error_payload = None

    except PayloadCPUError as exc:
        payload = None
        error_payload = PayloadInvalidoError(
            str(exc)
        )

    sincronizacion = ejecutar_con_reintentos_db(
        lambda: crear_sincronizacion(
            usuario_origen=usuario_origen
        )
    )

    def guardar():
        return _guardar_resultado_procesamiento(
            sincronizacion=sincronizacion,
            archivo=archivo,
            tipo_archivo=tipo_archivo,
            checksum=checksum,
            payload=payload,
            error_payload=error_payload,
        )

    try:
        archivo_procesado = (
            ejecutar_con_reintentos_db(
                guardar
            )
        )

    except IntegrityError:
        ejecutar_con_reintentos_db(
            lambda: sincronizacion.delete()
        )

        archivo_existente = (
            ejecutar_con_reintentos_db(
                lambda: buscar_archivo_por_checksum(
                    checksum
                )
            )
        )

        if archivo_existente:
            return archivo_existente, False

        raise

    except BaseDatosNoDisponibleError:
        raise

    except Exception as exc:
        error_original = exc

        ejecutar_con_reintentos_db(
            lambda: registrar_fallo_inesperado(
                sincronizacion=sincronizacion,
                exc=error_original,
            )
        )

        raise ProcesamientoInesperadoError(
            "Ocurrió un error inesperado "
            "durante el procesamiento."
        ) from error_original

    if error_payload is not None:
        raise error_payload

    return archivo_procesado, True


def ejecutar_remediacion(
    sincronizacion,
    accion_ejecutada,
    ejecutado_por,
    notas=None,
):
    resultado = AccionRemediacion.Resultado.FAILED

    try:
        with transaction.atomic():

            if accion_ejecutada == "RETRY_JOB":

                if sincronizacion.estado not in [
                    Sincronizacion.Estado.FAILED,
                    Sincronizacion.Estado.REJECTED,
                ]:
                    raise ValueError(
                        "La sincronización no se encuentra "
                        "en un estado reintentable."
                    )

                sincronizacion.estado = (
                    Sincronizacion.Estado.PENDING
                )

                sincronizacion.finalizado_at = None

                sincronizacion.save(
                    update_fields=[
                        "estado",
                        "finalizado_at",
                    ]
                )

            elif (
                accion_ejecutada
                == "FORCE_SKIP_VALIDATION"
            ):

                if (
                    sincronizacion.estado
                    != Sincronizacion.Estado.REJECTED
                ):
                    raise ValueError(
                        "Solo se puede omitir la validación "
                        "de una sincronización rechazada."
                    )

                sincronizacion.estado = (
                    Sincronizacion.Estado.COMPLETED
                )

                sincronizacion.finalizado_at = (
                    timezone.now()
                )

                sincronizacion.save(
                    update_fields=[
                        "estado",
                        "finalizado_at",
                    ]
                )

            else:
                raise ValueError(
                    "Acción de remediación no soportada."
                )

            resultado = (
                AccionRemediacion.Resultado.SUCCESS
            )

    except ValueError:
        AccionRemediacion.objects.create(
            sincronizacion=sincronizacion,
            accion_ejecutada=accion_ejecutada,
            ejecutado_por=ejecutado_por,
            resultado=AccionRemediacion.Resultado.FAILED,
            notas=notas,
        )

        raise

    return AccionRemediacion.objects.create(
        sincronizacion=sincronizacion,
        accion_ejecutada=accion_ejecutada,
        ejecutado_por=ejecutado_por,
        resultado=resultado,
        notas=notas,
    )