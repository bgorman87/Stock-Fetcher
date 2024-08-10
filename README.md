# Stock Fetcher

Stock Fetcher is a Python-based program designed to fetch and process stock data using yahooquery and web scraping data from MorningStar. The processed data is then stored in a PostgreSQL database.

This project is heavily related to and built to work alongside [Intrinsic](https://github.com/bgorman87/intrinsic). Due to the lengthy processing time for ~10k stock tickers, I run this on a separate server which is why its in its own repo. If desired you can integrate this entirely with Intrinsic to all run on the same machine and from the same compose file.

## Prerequisites
- Python 3.10 or higher
- Docker and Docker Compose
- PostgreSQL database

## Configuration

### Docker
The Docker Compose file is configured to use the following environment variables:
- `DATABASE_USER` - The username for the PostgreSQL database
- `DATABASE_PASSWORD` - The password for the PostgreSQL database
- `DATABASE_NAME` - The name of the PostgreSQL database
- `DATABASE_HOST` - The hostname of the PostgreSQL database
- `DATABASE_PORT` - The port of the PostgreSQL database

An example `.env.dev` file is provided in the repository. You can copy this file to `.env` and modify the values as needed.

### PostgreSQL
As indicated, this program is heavily reliant on [Intrinsic](https://github.com/bgorman87/intrinsic), specifically the database schema. You will need to have the Intrinsic database schema setup in your PostgreSQL database. The schema can be found in the [Intrinsic/database/schema.sql](https://github.com/bgorman87/Intrinsic/blob/master/database/schema.sql) file.


## Installation
1. Create a PostgreSQL database with the schema noted above, or install [Intrinsic](https://github.com/bgorman87/intrinsic) following the instructions in the README. Ensure the database is accessible from the host machine running this Docker container.
    - Note: If using a separate database or Docker container, you may need to edit or remove the `networks` sections in the `docker-compose.yml` file.
2. Clone the repository

    ```bash
    git clone https://github.com/bgorman87/stonks.git
    cd stonks
    ```
3. Modify the `.env` file as needed.
4. Build the Docker container

    ```bash
    docker-compose up --build
    ```
    This command will build the Docker image and start the container. The program will first attempt to connect to the PostgreSQL database, and if successful will then start processing stock data and storing it.

## Usage

This program is designed to run as a background process, fetching and processing stock data at regular intervals. Since this program is used for intrinsic long-term stock valuations, it really only needs to be run every once and a while. You can schedule it using a cron job on the host machine or manually run the Docker container as needed.

### Manually Running the Program

To manually run the Docker container, use the following command:

```bash
docker compose up -d
```

### Automatically Running the Program 

To automatically run the program, you can use a cron job to start the Docker container at regular intervals. For example, to run the program every day at 12:00 AM, you can add the following cron job:

- Edit crontab file:
    ```bash
    crontab -e
    ```
- Add the following line to the crontab file:
    ```bash
    0 0 * * * docker compose -f /absolute/path/to/docker-compose.yml up
    ```