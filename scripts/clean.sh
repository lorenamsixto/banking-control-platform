#!/bin/bash

set -e

echo "Deteniendo servicios..."

docker compose down --remove-orphans

echo "Entorno detenido correctamente."