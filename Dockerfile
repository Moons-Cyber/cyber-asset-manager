FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DADOS_DIR=/dados

WORKDIR /app


RUN useradd --create-home --uid 1000 app \
 && mkdir /dados \
 && chown app:app /dados


COPY requirements.txt .
RUN pip install -r requirements.txt


COPY servidor.py ./
COPY src ./src

USER app

VOLUME /dados
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/saude', timeout=3)" || exit 1


CMD ["gunicorn", \
     "--workers", "1", \
     "--threads", "8", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "servidor:app"]
