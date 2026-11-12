# Approximate replica of the evaluation image (gcr.io/kaggle-playground-170215/swebench-sandbox, private).
# What the harness code tells us: Python 3.12, git, pytest; the harness mounts /workspace,
# copies the wheels into /wheels and runs the container without network, with 2 CPUs and 4 GB.
# Repository dependencies: the same as the local environment where the oracle passed 65/104.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git patch && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
# Only needed to build the image behind a proxy (the evaluation container runs without network).
COPY ca-proxy.crt /usr/local/share/ca-certificates/ca-proxy.crt
ENV PIP_CERT=/usr/local/share/ca-certificates/ca-proxy.crt
RUN pip install --no-cache-dir -r /tmp/requirements.txt || \
    (while read -r l; do pip install --no-cache-dir --no-deps "$l" || echo "could not install: $l"; done < /tmp/requirements.txt)
RUN git config --global user.email sandbox@local && git config --global user.name sandbox && \
    git config --global --add safe.directory '*'
WORKDIR /workspace
# The evaluation runs /sandbox/setup.py --fast-path <repo> to install test dependencies (official script, not public).
# Here the dependencies are already in the image: an empty setup.py.
RUN mkdir -p /sandbox && printf 'import sys\nprint("setup.py replica: deps preinstaladas", sys.argv[1:])\n' > /sandbox/setup.py
