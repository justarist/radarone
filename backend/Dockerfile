ARG PYTHON_IMAGE=python:3.13.11-slim
FROM ${PYTHON_IMAGE} AS base

ARG UID=1000
ARG GID=1000

RUN groupadd --gid ${GID} appgroup && \
    useradd  --uid ${UID} \
             --gid ${GID} \
             --create-home \
             --shell /bin/bash \
             --no-log-init \
             --comment "app user" \
             appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY start.sh /start.sh

RUN chown -R appuser:appgroup /app && \
    chown -R appuser:appgroup /app/logs && \
    chmod +x /start.sh
USER appuser

EXPOSE 8000
CMD ["/start.sh"]

