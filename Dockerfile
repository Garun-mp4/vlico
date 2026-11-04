FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --gid 10001 vlico && useradd --uid 10001 --gid vlico --create-home vlico
COPY backend/ ./
COPY wireframe/assets/ /app/public/assets/
COPY wireframe/styles.css wireframe/main.js /app/public/
COPY scripts/container-entrypoint.sh /app/entrypoint.sh
RUN mkdir -p /data/public /data/private /app/staticfiles && chown -R vlico:vlico /data /app/staticfiles && chmod +x /app/entrypoint.sh
USER vlico
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "gthread", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-"]
