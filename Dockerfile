FROM python:3.15-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential gettext \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY . .
# These dummy values exist only for build commands; no database is contacted.
RUN SECRET_KEY=build-only-dummy-key-not-for-runtime \
    DATABASE_URL=postgresql://build:build@localhost/build \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    python manage.py compilemessages

FROM python:3.15-slim-bookworm AS runtime

ARG GIT_SHA=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PATH="/opt/venv/bin:$PATH" \
    GIT_SHA=${GIT_SHA}

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --from=builder /app /app
RUN SECRET_KEY=build-only-dummy-key-not-for-runtime \
    DATABASE_URL=postgresql://build:build@localhost/build \
    python manage.py collectstatic --noinput \
    && chmod 755 bin/start.sh \
    && useradd --uid 10001 --no-create-home app

USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=4).close()"

ENTRYPOINT ["./bin/start.sh"]
# Clear the Python base image's default command so normal starts run start.sh.
CMD []

FROM runtime AS dev
USER root
RUN apt-get update \
    && apt-get install --no-install-recommends -y gettext \
    && rm -rf /var/lib/apt/lists/*
USER 10001

# Docker builds the last stage by default; CI and Render get the lean runtime.
FROM runtime AS production
