FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir requests pyarrow

COPY rpc_to_partitioned_parquet.py /app/rpc_to_partitioned_parquet.py

ENTRYPOINT ["python", "/app/rpc_to_partitioned_parquet.py"]