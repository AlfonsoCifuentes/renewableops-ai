FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system renewableops && useradd --system --gid renewableops renewableops
WORKDIR /app

COPY requirements.lock ./
RUN pip install --requirement requirements.lock

COPY pyproject.toml README.md ./
COPY packages/core/src ./packages/core/src
COPY apps/api/src ./apps/api/src
RUN pip install --no-deps .

USER renewableops
EXPOSE 8000
CMD ["uvicorn", "renewableops_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
