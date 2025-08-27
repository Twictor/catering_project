.PHONY: help worker-high worker-low worker-all celery-high-up celery-high-down celery-high-logs celery-low-up celery-low-down celery-low-logs flower-up flower-down
help:
    @echo "Available commands:"
    @echo "  worker-high    - Start a Celery worker for the high priority queue."
    @echo "  worker-low     - Start a Celery worker for the low priority queue."
    @echo "  worker-all     - Start a Celery worker for all queues."
    @echo "  celery-high-up    - Start Celery high priority worker with Docker."
    @echo "  celery-high-down  - Stop Celery high priority worker."
    @echo "  celery-high-logs  - View logs for Celery high priority worker."
    @echo "  celery-low-up     - Start Celery low priority worker with Docker."
    @echo "  celery-low-down   - Stop Celery low priority worker."
    @echo "  celery-low-logs   - View logs for Celery low priority worker."
    @echo "  flower-up         - Start Flower monitoring tool."
    @echo "  flower-down       - Stop Flower monitoring tool."

# Starts a worker for high-priority tasks (orders)
worker-high:
    celery -A config worker -l info -Q high_priority -c 1

# Starts a worker for low-priority tasks (emails)
worker-low:
    celery -A config worker -l info -Q low_priority -c 1

# You can also add a command to start a worker that listens to all queues
worker-all:
    celery -A config worker -l info -c 2

# Celery commands
celery-high-up:
    docker compose up -d celery_high

celery-high-down:
    docker compose stop celery_high

celery-high-logs:
    docker compose logs -f celery_high

celery-low-up:
    docker compose up -d celery_low

celery-low-down:
    docker compose stop celery_low

celery-low-logs:
    docker compose logs -f celery_low

# Flower monitoring
flower-up:
    docker compose up -d flower

flower-down:
    docker compose stop flower


run:
    python manage.py runserver

docker:
    docker compose up -d database cache brocker mailing


silpo_mock:
    python -m uvicorn silpo.mock.main:app --port 8001 --reload

kfc_mock:
    python -m uvicorn kfc.mock.main:app --port 8002 --reload

uklon_mock:
    python -m uvicorn uklon.mock.main:app --port 8003 --reload

uber_mock:
    python -m uvicorn uber.mock.main:app --port 8004 --reload