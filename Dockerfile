FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_DEBUG=1
ENV DJANGO_ALLOWED_HOSTS="*"

# Install system dependencies
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv sync

# Start application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS dev

RUN pipenv sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD ["manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS prod

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD ["-m", "gunicorn", "config.wsgi:application", "--bind", ":8000"]

# ====================================================================
# MULTI-STAGE BUILDS FOR PROVIDERS
# ====================================================================

FROM base AS silpo

RUN pipenv sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD ["-m", "uvicorn", "tests.providers.silpo:app", "--host", "0.0.0.0"]


FROM base AS kfc

RUN pipenv sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD ["-m", "uvicorn", "tests.providers.kfc:app", "--host", "0.0.0.0"]


FROM base AS uklon

RUN pipenv sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD ["-m", "uvicorn", "tests.providers.uklon:app", "--host", "0.0.0.0"]


FROM base AS api

EXPOSE 8000


FROM base AS kfc_mock

EXPOSE 8001

# Install dependencies for kfc_mock
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv sync --dev # Install dev dependencies as fastapi is a dev dependency

WORKDIR /app/tests/providers

COPY ./tests/providers/kfc.py /app/tests/providers/kfc.py

CMD ["fastapi", "run", "kfc:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]


FROM base AS uklon_mock

EXPOSE 8002