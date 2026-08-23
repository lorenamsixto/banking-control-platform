# Banking Control Platform

Plataforma de control y monitoreo de sincronizaciones bancarias desarrollada como prueba técnica.

La solución permite procesar archivos JSON, controlar ejecuciones de sincronización, aplicar idempotencia mediante SHA-256, registrar errores con trazabilidad mediante `correlation_id`, consultar métricas operativas y ejecutar acciones de remediación.

---

## Tecnologías

### Backend

- Python 3.11
- Django 5
- Django REST Framework
- PostgreSQL 17
- Pytest
- pytest-django
- pytest-cov
- ProcessPoolExecutor

### Frontend

- React 19
- TypeScript 6
- Vite 8
- PrimeReact 10.9.8
- PrimeIcons 7
- Axios

### Infraestructura

- Docker
- Docker Compose
- Bash
- Jenkins

---

## Arquitectura

```mermaid
flowchart LR

    U[Usuario / Navegador]

    subgraph FRONTEND_NET[frontend_net]
        F[React + Vite]
        B[Django REST Framework]
    end

    subgraph DATABASE_NET[database_net]
        DB[(PostgreSQL 17)]
    end

    U -->|HTTP :5173| F
    F -->|REST API :8000| B
    B -->|PostgreSQL :5432| DB