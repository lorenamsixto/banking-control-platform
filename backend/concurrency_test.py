import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


URL = "http://127.0.0.1:8000/api/procesar/"
TOTAL_PETICIONES = 6


def enviar_archivo(numero):
    contenido = [
        {
            "producto": f"Producto concurrente {numero}",
            "cantidad": numero + 1,
            "total": (numero + 1) * 1000,
        }
    ]

    archivo_json = json.dumps(contenido).encode("utf-8")

    files = {
        "archivo": (
            f"concurrencia_{numero}.json",
            archivo_json,
            "application/json",
        )
    }

    data = {
        "tipo_archivo": "ventas",
        "usuario_origen": "prueba_concurrencia",
    }

    inicio = time.perf_counter()

    try:
        response = requests.post(
            URL,
            files=files,
            data=data,
            timeout=30,
        )

        duracion = time.perf_counter() - inicio

        return {
            "peticion": numero,
            "status": response.status_code,
            "tiempo": duracion,
            "respuesta": response.json(),
        }

    except Exception as exc:
        duracion = time.perf_counter() - inicio

        return {
            "peticion": numero,
            "status": "ERROR",
            "tiempo": duracion,
            "respuesta": str(exc),
        }


def main():
    print(f"\nEnviando {TOTAL_PETICIONES} peticiones simultáneas...\n")

    inicio_total = time.perf_counter()

    with ThreadPoolExecutor(
        max_workers=TOTAL_PETICIONES
    ) as executor:

        futuros = [
            executor.submit(enviar_archivo, numero)
            for numero in range(1, TOTAL_PETICIONES + 1)
        ]

        for futuro in as_completed(futuros):
            resultado = futuro.result()

            print(
                f"Petición {resultado['peticion']} | "
                f"HTTP {resultado['status']} | "
                f"{resultado['tiempo']:.3f} s"
            )

            if isinstance(resultado["respuesta"], dict):
                print(
                    "  idempotente:",
                    resultado["respuesta"].get("idempotente"),
                )

    duracion_total = time.perf_counter() - inicio_total

    print(
        f"\nTiempo total: {duracion_total:.3f} segundos"
    )


if __name__ == "__main__":
    main()