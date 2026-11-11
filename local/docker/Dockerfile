# Réplica aproximada de la imagen del examen (gcr.io/kaggle-playground-170215/swebench-sandbox, privada).
# Lo que sabemos por el código del harness: Python 3.12, git, pytest; el harness monta /workspace,
# copia los wheels en /wheels y lanza el contenedor sin red, con 2 CPU y 4 GB.
# Dependencias de los repos: las mismas del entorno local donde el oráculo pasó 65/104.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git patch && rm -rf /var/lib/apt/lists/*
COPY requisitos.txt /tmp/requisitos.txt
# Solo para construir la imagen detrás del proxy de esta sesión (el contenedor del examen corre sin red).
COPY ca-proxy.crt /usr/local/share/ca-certificates/ca-proxy.crt
ENV PIP_CERT=/usr/local/share/ca-certificates/ca-proxy.crt
RUN pip install --no-cache-dir -r /tmp/requisitos.txt || \
    (while read -r l; do pip install --no-cache-dir --no-deps "$l" || echo "no se pudo: $l"; done < /tmp/requisitos.txt)
RUN git config --global user.email sandbox@local && git config --global user.name sandbox && \
    git config --global --add safe.directory '*'
WORKDIR /workspace
# El examen ejecuta /sandbox/setup.py --fast-path <repo> para instalar dependencias de tests (script oficial, no público).
# Aquí las dependencias ya están en la imagen: un setup.py vacío.
RUN mkdir -p /sandbox && printf 'import sys\nprint("setup.py replica: deps preinstaladas", sys.argv[1:])\n' > /sandbox/setup.py
