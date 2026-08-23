#!/bin/bash

set -e

echo "Levantando Banking Control Platform..."

docker compose up --build -d

echo "Esperando servicios..."

sleep 5

docker compose ps

echo "Entorno iniciado correctamente."