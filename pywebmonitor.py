import argparse
import asyncio
import configparser
import csv
import logging
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

import aiohttp
import psycopg2
from psycopg2 import sql


def setup_logging(logfile: str) -> None:
    """Sets up basic logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(logfile), logging.StreamHandler()],
    )


def read_config(
    config_file: str, section: str = "Database"
) -> dict[str, str | None] | None:
    """Reads the section part of the INI config file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    return dict(config[section])


def read_db_environment_variables() -> dict[str, str | None]:
    """Reads DB environment variables"""
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    dbname = os.environ.get("DB_NAME")
    tablename = os.environ.get("DB_TABLENAME")
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": dbname,
        "tablename": tablename,
    }


def parse_arguments():
    """parse the arguments of the script."""
    parser = argparse.ArgumentParser(description="Web Monitoring Script")
    parser.add_argument(
        "-c", "--config", default="config.ini", help="Path to the configuration file"
    )
    parser.add_argument(
        "-u",
        "--urls",
        required=True,
        help="Path to the CSV file containing URLs, interval, and regex pattern",
    )
    parser.add_argument(
        "-l",
        "--logfile",
        default="webmonitor.log",
        help="Path to the logfile",
    )
    args = parser.parse_args()
    return args


def get_db_params(filepath: str) -> dict[str, str | None] | None:
    if os.path.exists(filepath):
        try:
            return read_config(filepath)
        except configparser.Error as e:
            logging.error(f"Error reading configuration file: {e}")
        except KeyError as e:
            logging.error(f"Error finding the section: {e}")

        return None
    else:
        logging.info(
            "Config file not found at {}. Trying environment variables...".format(
                filepath
            )
        )
        return read_db_environment_variables()


def read_urls(filepath: str) -> list[list[str]] | None:
    """Reads the URLS from the given CSV file"""
    try:
        with open(filepath, "r") as csvfile:
            reader = csv.reader(csvfile)
            urls_data = [row for row in reader]
        return urls_data
    except FileNotFoundError:
        logging.error(f'Error: URLs file "{filepath}" not found.')
    except csv.Error as e:
        logging.error(f'Error reading CSV file "{filepath}": {e}')
    except Exception as e:
        logging.exception(f"Unexpected error while reading URLs file:")

    return None


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def is_valid_interval(interval: str, min_val: int = 5, max_val: int = 300) -> bool:
    """Checks if the interval can be converted to int and it's between min and max values"""
    try:
        interval_val = int(interval)
        return isinstance(interval_val, int) and min_val <= interval_val <= max_val
    except ValueError:
        return False


def is_valid_regex(regex_pattern: str) -> bool:
    """Checks if the pattern is a valid regex_pattern or None"""
    if regex_pattern is None:
        return True
    try:
        re.compile(regex_pattern)
        return True
    except re.error:
        return False


def validate_urls(urls_data: list[tuple]) -> list:
    """Validates the format of URLs data"""
    validated_urls = []

    for url, interval, regex_pattern in urls_data:
        if (
            is_valid_url(url)
            and is_valid_interval(interval)
            and is_valid_regex(regex_pattern)
        ):
            validated_urls.append((url, int(interval), regex_pattern))
        else:
            logging.warning(f"Invalid URL data: {url}, {interval}, {regex_pattern}")

    return validated_urls


def connect_to_database(db_params: dict[str, str]):
    """Establishes a connection to the database."""
    try:
        connection = psycopg2.connect(
            host=db_params["host"],
            port=db_params["port"],
            user=db_params["user"],
            password=db_params["password"],
            dbname=db_params["dbname"],
        )
        return connection
    except psycopg2.Error as e:
        logging.error(f"Error connecting to the database: {e}")
        return None


def create_table_if_not_exists(connection, tablename: str):
    """Creates a table for storing monitoring results if it doesn't exist."""
    try:
        connstring = """
            CREATE TABLE IF NOT EXISTS {table} (
                id SERIAL PRIMARY KEY,
                url VARCHAR(255),
                status INT,
                regex_match BOOLEAN,
                response_time FLOAT,
                page_content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """.format(
            table=tablename
        )
        logging.debug(f"This is the connstring:\n{connstring}")
        with connection.cursor() as cursor:
            cursor.execute(connstring)
        connection.commit()
    except psycopg2.Error as e:
        logging.error(f"Error creating the table: {e}")


def write_to_db(
    url,
    http_status,
    regex_match,
    response_time,
    content,
    database_connection,
    tablename,
):
    """Write the content to the database"""
    try:
        with database_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "INSERT INTO {} (url, status, regex_match, response_time, page_content) VALUES (%s, %s, %s, %s, %s)"
                ).format(sql.Identifier(tablename)),
                [
                    url,
                    http_status,
                    regex_match,
                    response_time,
                    content,
                ],
            )
        database_connection.commit()
    except psycopg2.Error as db_error:
        logging.exception(f"Database error:")

    logging.debug(
        "{} with response_time {} has been written to the DB successfully.".format(
            url, response_time
        )
    )


async def monitor_urls(url, regex_pattern, interval, database_connection, tablename):
    """
    Monitor URLs in a concurrent way.
    Asynchronously get the URLs, check for regex match, and then write the result to the DB.
    Writing to DB uses the same connection for now. Doesn't break the concurrency.
    """
    while True:
        async with aiohttp.ClientSession() as session:
            start_time = datetime.now()
            logging.debug(f"Start time {start_time} for url {url}")

            async with session.get(url) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()

                http_status = response.status
                content = await response.text()
                logging.debug("Response received for %s", url)
                logging.debug(
                    f"End time {end_time} for url {url}, took {response_time} seconds"
                )
                logging.debug("Body: {}...".format(content[:15]))
                regex_match = None
                if regex_pattern is not None:
                    regex_match = bool(re.search(regex_pattern, content))

                write_to_db(
                    url,
                    http_status,
                    regex_match,
                    response_time,
                    content,
                    database_connection,
                    tablename,
                )

        logging.debug(
            "Sleeping now for {} with response_time:{} for {} seconds".format(
                url, response_time, interval
            )
        )
        await asyncio.sleep(interval)
        logging.debug("Woke up for {} after {} seconds.".format(url, interval))


async def main_async_monitor_urls(urls: list, database_connection, tablename: str):
    """Asynchronously monitor multiple URLs."""
    tasks = [
        monitor_urls(url, regex_pattern, interval, database_connection, tablename)
        for url, interval, regex_pattern in urls
    ]
    await asyncio.gather(*tasks)


def main():
    args = parse_arguments()

    # Set up logging
    setup_logging(args.logfile)

    # Get DB Params
    db_params = get_db_params(args.config)
    if db_params == None:
        sys.exit()
    logging.debug("Database parameters: %s", db_params)

    # Connect to the database
    db_connection = connect_to_database(db_params)
    if db_connection is None:
        sys.exit()
    logging.info("Connected to the {} database.".format(db_params["dbname"]))

    # Create monitoring results table if not exists
    create_table_if_not_exists(db_connection, db_params["tablename"])
    logging.info(
        "Ensured that the {} table exists in {} database.".format(
            db_params["tablename"], db_params["dbname"]
        )
    )

    # Check if the URLs file exists
    urls_data = read_urls(args.urls)
    logging.info(f'URLs file "{args.urls}" read successfully.')

    # Validate the URLs
    validated_urls = validate_urls(urls_data)
    logging.debug("Validated URLs: %s", validated_urls)

    if len(validated_urls) == 0:
        logging.info("There are no Valid URLs to check, exiting...")
        sys.exit()

    logging.info("Monitoring the URLs now.")

    # Run the main_async function to asynchronously monitor URLs
    try:
        asyncio.run(
            main_async_monitor_urls(
                validated_urls, db_connection, db_params["tablename"]
            )
        )
    except KeyboardInterrupt:
        logging.info("Monitoring interrupted. Exiting...")


if __name__ == "__main__":
    main()
