import hashlib
import json
import random
import time

from django.utils import timezone
from django.db import IntegrityError, OperationalError, close_old_connections, transaction
from .models import AccionRemediacion, ArchivoProcesado, Sincronizacion, LogError

from concurrent.futures import ThreadPoolExecutor

CPU_EXECUTOR = ThreadPoolExecutor(max_workers=4)

def calcular_checksum(archivo):
    sha256 = hashlib.sha256()

    for chunk in archivo.chunks():
        sha256.update(chunk)

    archivo.seek(0)

    return sha256.hexdigest()

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

def _guardar_resultado_procesamiento(
    archivo,
    tipo_archivo,
    usuario_origen,
    checksum,
    payload=None,
    error_payload=None,
):
    with transaction.atomic():
        sincronizacion = crear_sincronizacion(
            usuario_origen=usuario_origen,
        )

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

            sincronizacion.estado = Sincronizacion.Estado.REJECTED

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

            sincronizacion.estado = Sincronizacion.Estado.COMPLETED

        sincronizacion.finalizado_at = timezone.now()

        sincronizacion.save(
            update_fields=[
                "estado",
                "finalizado_at",
            ]
        )

        return archivo_procesado



    checksum = ejecutar_checksum_async(archivo)

    archivo_existente = buscar_archivo_por_checksum(checksum)

    if archivo_existente:
        return archivo_existente, False

    payload_invalido = None
    archivo_procesado = None

    try:
        with transaction.atomic():

            sincronizacion = crear_sincronizacion(
                usuario_origen=usuario_origen,
            )

            sincronizacion.estado = Sincronizacion.Estado.RUNNING
            sincronizacion.save(
                update_fields=["estado"]
            )

            try:
                payload = ejecutar_parseo_async(archivo)

            except PayloadInvalidoError as exc:
                payload_invalido = exc

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
                    mensaje=str(exc),
                )

                sincronizacion.estado = Sincronizacion.Estado.REJECTED
                sincronizacion.finalizado_at = timezone.now()

                sincronizacion.save(
                    update_fields=[
                        "estado",
                        "finalizado_at",
                    ]
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

                sincronizacion.estado = Sincronizacion.Estado.COMPLETED
                sincronizacion.finalizado_at = timezone.now()

                sincronizacion.save(
                    update_fields=[
                        "estado",
                        "finalizado_at",
                    ]
                )

    except IntegrityError:
        archivo_existente = buscar_archivo_por_checksum(checksum)

        if archivo_existente:
            return archivo_existente, False

        raise

    if payload_invalido is not None:
        raise payload_invalido

    return archivo_procesado, True

def procesar_archivo(archivo, tipo_archivo, usuario_origen):
    checksum = ejecutar_checksum_async(archivo)

    archivo_existente = ejecutar_con_reintentos_db(
        lambda: buscar_archivo_por_checksum(checksum)
    )

    if archivo_existente:
        return archivo_existente, False

    try:
        payload = ejecutar_parseo_async(archivo)
        error_payload = None

    except PayloadInvalidoError as exc:
        payload = None
        error_payload = exc

    def guardar():
        return _guardar_resultado_procesamiento(
            archivo=archivo,
            tipo_archivo=tipo_archivo,
            usuario_origen=usuario_origen,
            checksum=checksum,
            payload=payload,
            error_payload=error_payload,
        )

    try:
        archivo_procesado = ejecutar_con_reintentos_db(
            guardar
        )

    except IntegrityError:
        archivo_existente = ejecutar_con_reintentos_db(
            lambda: buscar_archivo_por_checksum(checksum)
        )

        if archivo_existente:
            return archivo_existente, False

        raise

    if error_payload is not None:
        raise error_payload

    return archivo_procesado, True

# El archivo recibido es inválido.
class PayloadInvalidoError(Exception):
    pass

# PostgreSQL no está disponible después de los reintentos.
class BaseDatosNoDisponibleError(Exception):
    pass

def parsear_payload(archivo):
    try:
        contenido = archivo.read()

        if not contenido:
            raise PayloadInvalidoError(
                "El archivo está vacío."
            )

        try:
            texto = contenido.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PayloadInvalidoError(
                "El archivo no contiene texto UTF-8 válido."
            ) from exc

        try:
            payload = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise PayloadInvalidoError(
                "El archivo contiene JSON inválido."
            ) from exc

        if not isinstance(payload, list):
            raise PayloadInvalidoError(
                "El payload debe contener una lista de registros."
            )

        for indice, registro in enumerate(payload):
            if not isinstance(registro, dict):
                raise PayloadInvalidoError(
                    f"El registro en la posición {indice} "
                    "debe ser un objeto JSON."
                )

        return payload

    finally:
        archivo.seek(0)

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
                        "La sincronización no se encuentra en un estado reintentable."
                    )

                sincronizacion.estado = Sincronizacion.Estado.PENDING
                sincronizacion.finalizado_at = None

                sincronizacion.save(
                    update_fields=[
                        "estado",
                        "finalizado_at",
                    ]
                )

            elif accion_ejecutada == "FORCE_SKIP_VALIDATION":
                if sincronizacion.estado != Sincronizacion.Estado.REJECTED:
                    raise ValueError(
                        "Solo se puede omitir la validación de una sincronización rechazada."
                    )

                sincronizacion.estado = Sincronizacion.Estado.COMPLETED
                sincronizacion.finalizado_at = timezone.now()

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

            resultado = AccionRemediacion.Resultado.SUCCESS

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

def procesar_contenido_archivo(archivo):
    checksum = calcular_checksum(archivo)
    payload = parsear_payload(archivo)

    return checksum, payload

def ejecutar_procesamiento_cpu(archivo):
    future = CPU_EXECUTOR.submit(
        procesar_contenido_archivo,
        archivo,
    )

    return future.result()

def ejecutar_checksum_async(archivo):
    future = CPU_EXECUTOR.submit(
        calcular_checksum,
        archivo,
    )

    return future.result()

def ejecutar_parseo_async(archivo):
    future = CPU_EXECUTOR.submit(
        parsear_payload,
        archivo,
    )

    return future.result()

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
                raise BaseDatosNoDisponibleError("La base de datos no está disponible.") from exc

            delay_exponencial = base_delay * (2 ** intento)
            jitter = random.uniform(0, base_delay)

            time.sleep(delay_exponencial + jitter)
