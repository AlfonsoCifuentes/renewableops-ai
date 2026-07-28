FROM ghcr.io/mlflow/mlflow:v3.1.1

RUN pip install --no-cache-dir \
    "boto3==1.43.58" \
    "psycopg[binary]==3.3.4" \
    && groupadd --system --gid 10001 mlflow \
    && useradd --system --uid 10001 --gid mlflow --home-dir /tmp mlflow

USER mlflow
