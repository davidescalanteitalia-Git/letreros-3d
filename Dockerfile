# Letreros 3D Studio · web + motor de geometría en un solo contenedor (puerto 80, como antes).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/motor:/app

WORKDIR /app
COPY motor/requirements.txt motor/requirements.txt
COPY servidor/requirements.txt servidor/requirements.txt
RUN pip install -r motor/requirements.txt -r servidor/requirements.txt

COPY motor/letreros_motor motor/letreros_motor
COPY motor/fuentes motor/fuentes
COPY servidor/__init__.py servidor/app.py servidor/
COPY servidor/estaticos servidor/estaticos
COPY index.html .

# Comprobación en la construcción: la fuente coincide con su SHA-256 y el motor genera una pieza.
RUN python -c "import letreros_motor as m; p = m.generar_letrero(m.Diseno('A')); assert p.piezas[0].malla.is_watertight" \
 && useradd --system --uid 10001 --no-create-home letreros
USER letreros

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1/api/salud', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "servidor.app:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers", "--forwarded-allow-ips", "*", "--workers", "1"]
