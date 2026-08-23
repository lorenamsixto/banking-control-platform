#!/bin/bash

set -e

echo "Realizando limpieza destructiva del entorno..."

docker compose down -v --remove-orphans

echo "Contenedores, redes y volúmenes eliminados correctamente."