FROM debian:bookworm-slim AS builder

WORKDIR /

ENV APP_HOME=/dcbot \
    APP_USER=dcbot \
    APP_GROUP=dcbot

RUN groupadd -r ${APP_GROUP} && \
    useradd -r -d ${APP_HOME} -m -g ${APP_GROUP} ${APP_USER}

RUN export DEBIAN_FRONTEND=noninteractive; \
    apt-get -q update \
    && apt-get -q install -y \
    -o APT::Install-Suggests=false \
    -o APT::Install-Recommends=false \
    python3-pip \
    python3 \
    python3-venv \
    python3-dev \
    libffi-dev \
    libnacl-dev \
    && rm -rf /var/lib/apt/lists/*

USER ${APP_USER}
WORKDIR ${APP_HOME}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --chown=${APP_USER}:${APP_GROUP} requirements.txt .

RUN python3 -m venv .env \
    && . .env/bin/activate \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade -r ${APP_HOME}/requirements.txt

COPY --chown=${APP_USER}:${APP_GROUP} bot bot
COPY --chown=${APP_USER}:${APP_GROUP} entrypoint.py entrypoint.py

RUN mkdir -p ${APP_HOME}/logs

FROM gcr.io/distroless/python3-debian12 AS runtime

ENV APP_HOME=/dcbot \
    APP_USER=dcbot \
    APP_GROUP=dcbot

COPY --from=builder --chown=0:0 /etc/passwd /etc/passwd
COPY --from=builder --chown=0:0 /etc/group /etc/group

COPY --from=builder --chown=${APP_USER}:${APP_GROUP} ${APP_HOME} ${APP_HOME}

USER ${APP_USER}
WORKDIR ${APP_HOME}

ENV PATH=${APP_HOME}/.env/bin:${PATH} \
    PYTHONPATH=${APP_HOME}/bot \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT [ "/dcbot/.env/bin/python3" ]
CMD [ "entrypoint.py" ]