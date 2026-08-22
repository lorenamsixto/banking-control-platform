import hashlib
import json

import pytest

from sync.cpu_tasks import (
    PayloadCPUError,
    calcular_checksum_bytes,
    parsear_payload_bytes,
)


def test_calcular_checksum_bytes():
    contenido = b"hola"

    resultado = calcular_checksum_bytes(contenido)

    esperado = hashlib.sha256(contenido).hexdigest()

    assert resultado == esperado
    assert len(resultado) == 64


def test_parsear_payload_valido():
    contenido = json.dumps(
        [
            {"producto": "Laptop", "cantidad": 2},
            {"producto": "Mouse", "cantidad": 4},
        ]
    ).encode("utf-8")

    resultado = parsear_payload_bytes(contenido)

    assert isinstance(resultado, list)
    assert len(resultado) == 2
    assert resultado[0]["producto"] == "Laptop"


def test_parsear_payload_vacio():
    with pytest.raises(
        PayloadCPUError,
        match="El archivo está vacío.",
    ):
        parsear_payload_bytes(b"")


def test_parsear_payload_json_invalido():
    contenido = b'[{"producto": "Laptop", "cantidad": }]'

    with pytest.raises(
        PayloadCPUError,
        match="El archivo contiene JSON inválido.",
    ):
        parsear_payload_bytes(contenido)


def test_parsear_payload_no_es_lista():
    contenido = json.dumps(
        {"producto": "Laptop"}
    ).encode("utf-8")

    with pytest.raises(
        PayloadCPUError,
        match="El payload debe contener una lista de registros.",
    ):
        parsear_payload_bytes(contenido)


def test_parsear_payload_registro_no_es_objeto():
    contenido = json.dumps(
        [
            {"producto": "Laptop"},
            "registro_invalido",
        ]
    ).encode("utf-8")

    with pytest.raises(
        PayloadCPUError,
        match="debe ser un objeto JSON",
    ):
        parsear_payload_bytes(contenido)