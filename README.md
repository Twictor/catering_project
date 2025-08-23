# Catering Project

## Getting Started

1.  **Install Docker and Docker Compose:** Make sure you have Docker and Docker Compose installed on your system.  You can find instructions on how to install them on the [Docker website](https://docs.docker.com/get-docker/).

2.  **Create a .env file:** Create a copy of the `.env.example` file and rename it to `.env`.  Fill in the required environment variables in the `.env` file.

    ```bash
    cp .env.example .env
    # Then, edit .env and fill in the values
    nano .env
    ```

    Example `.env` file:

    ```
    DJANGO_SECRET_KEY=your_secret_key
    DJANGO_DEBUG=True
    DJANGO_ALLOWED_HOSTS=*
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_DB=catering_db
    REDIS_HOST=cache
    REDIS_PORT=6379
    ```

3.  **Run the application:** Use Docker Compose to build and start the application.

    ```bash
    docker compose up --build
    ```

    This command will build the Docker images and start the containers defined in the `compose.yaml` file.

4.  **Access the application:** Once the containers are running, you can access the application in your browser at `http://localhost`. (The exact URL may vary depending on your configuration.)

## Requirements

*   Docker
*   Docker Compose