#!/bin/bash

set -e

echo "Ejecutando tests del backend..."

docker compose exec backend pytest -q

echo "Validando build del frontend..."

docker compose exec frontend npm run build

echo "Pruebas completadas correctamente."