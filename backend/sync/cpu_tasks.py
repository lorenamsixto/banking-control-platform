import hashlib
import json


class PayloadCPUError(Exception):
    pass


def calcular_checksum_bytes(contenido):
    return hashlib.sha256(contenido).hexdigest()


def parsear_payload_bytes(contenido):
    if not contenido:
        raise PayloadCPUError(
            "El archivo está vacío."
        )

    try:
        texto = contenido.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayloadCPUError(
            "El archivo no contiene texto UTF-8 válido."
        ) from exc

    try:
        payload = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise PayloadCPUError(
            "El archivo contiene JSON inválido."
        ) from exc

    if not isinstance(payload, list):
        raise PayloadCPUError(
            "El payload debe contener una lista de registros."
        )

    for indice, registro in enumerate(payload):
        if not isinstance(registro, dict):
            raise PayloadCPUError(
                f"El registro en la posición {indice} "
                "debe ser un objeto JSON."
            )

    return payload