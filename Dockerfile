# ==============================================================================
# HipoRefi-CL: Dockerfile de Producción Multi-Servicio
# Soporta tanto API REST (FastAPI/Uvicorn) como Dashboard Interactivo (Streamlit)
# ==============================================================================

FROM python:3.11-slim AS base

# Configuración del entorno de Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# Instalar dependencias del sistema necesarias (curl para healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario sin privilegios para ejecución segura
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Copiar archivos de definición de dependencias para aprovechar la caché de capas
COPY --chown=appuser:appuser pyproject.toml README.md ./

# Instalar dependencias del proyecto (incluyendo dev y scrapers si se requiere)
RUN pip install --upgrade pip && \
    pip install .

# Copiar el código fuente y scripts
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser data/ ./data/
COPY --chown=appuser:appuser scripts/ ./scripts/

# Instalar el paquete en modo editable local
RUN pip install -e .

# Cambiar a usuario no root
USER appuser

# Exponer puertos para API (8000) y Dashboard (8501)
EXPOSE 8000 8501

# Healthcheck predeterminado contra la API
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Comando por defecto: Iniciar la API REST
CMD ["uvicorn", "src.app.api:app", "--host", "0.0.0.0", "--port", "8000"]
