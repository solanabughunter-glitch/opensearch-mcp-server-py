FROM python:3.10-slim AS builder

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ ./src/

ENV PYTHONUNBUFFERED=1 \
    LOG_CORRELATION_HOST=0.0.0.0 \
    LOG_CORRELATION_PORT=8765

EXPOSE 8765

CMD ["python", "-c", "import sys; sys.path.insert(0, 'src'); from tools.log_correlation_server import main; main()"]
