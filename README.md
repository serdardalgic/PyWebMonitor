# PyWebMonitor

PyWebMonitor is a simple program that monitors the availability of websites on the internet, produces metrics about them and stores the results in a Postgresql DB.

```
% python pywebmonitor.py --help
usage: pywebmonitor.py [-h] [-c CONFIG] -u URLS [-l LOGFILE]

Web Monitoring Script

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to the configuration file
  -u URLS, --urls URLS  Path to the CSV file containing URLs, interval, and regex pattern
  -l LOGFILE, --logfile LOGFILE
                        Path to the logfile

```

## Background Story:

This task was an assignment for an interview I had with a company whose name I'm not allowed to share. But, I can share the code without any references to the company, so, here it is. I hope anybody can use it for educational purposes, or anything they see fit. You can safely assume that anything that's not implemented is because of the tight schedule.

> Your task is to implement a program that monitors the availability of many websites over the network, produces metrics about these and stores the metrics into a PostgreSQL database.

> The website monitor should perform the checks periodically and collect the request timestamp, the response time, the HTTP status code, as well as optionally checking the returned page
contents for a regex pattern that is expected to be found on the page. Each URL should be checked periodically, with the ability to configure the interval (between 5 and 300 seconds) and
the regexp on a per-URL basis. The monitored URLs can be anything found online. In case the check fails the details of the failure should be logged into the database.

> The solution should NOT include using any of the following:
>
> ● Database ORM libraries - use a Python DB API or similar library and raw SQL queries instead.
>
> ● External Scheduling libraries - we really want to see your take on concurrency.
>
> ● Extensive container build recipes - rather focus your effort on the Python code, tests, documentation, etc.

## Installation

To be able to run this program, please use a modern Python3 version, preferably Python 3.11.x or higher.

Create a virtual environment and install the requirements inside this virtual environment. For example:
```
$> python3 -m venv new_virtual_env
$> source new_virtual_env/bin/activate
$> pip install -r requirements.txt
```

Now you can run PyWebMonitor by providing a csv file that contains URLs.

## Configuration

You can provide database configuration either in a config file or with the environment variables. [A sample config file](sample-config.ini) is provided.

## Logging

If not provided, the program writes logs to the `webmonitor.log` file. You can change the logfile path by giving a new path to the program with the `-l` argument.
You can modify the log level in setup_logging function for debugging purposses.

## URLs File

URLs are provided via a CSV file. The format of the file is:
```
<A Valid URL>, <Integer value between 5 and 300>, <A valid Regex pattern>
```
[A sample CSV file](sample-URLs.csv) is provided.
Invalid URLs will be ruled out. For example:
```
2023-12-26 11:37:44,407 [WARNING] Invalid URL data: https://example.com,  NaN,  "hede"
```

## Testing

A series of tests have been written in the [test_pywebmonitor.py](test_pywebmonitor.py) file. They can be run with pytest (assuming pytest executable is reachable, if not, `pip install pytest`)
```
pytest test_pywebmonitor.py
```
Tests do not cover all the test cases and scenarios, especially for DB writes and the async.io tasks.
For database tests, [pytest-postgresql](https://pypi.org/project/pytest-postgresql/) can be used.
For async.io tests, [pytest-asyncio](https://pypi.org/project/pytest-asyncio/) can be used.

### Useful Resources

Here are some articles, blog posts, documentation and tools that helped/inspired me while coding this script
* https://docs.python.org/3/library/asyncio.html
* https://www.zenrows.com/blog/asynchronous-web-scraping-python
* https://www.psycopg.org/psycopg3/docs/advanced/async.html

### Next Steps

Here are some of my thoughts on what can be done as next steps in this project:

* Test improvements
* Maybe connection pooling for postgresql connections
* Asynchronous DB writes (using [psycopg3](https://www.psycopg.org/psycopg3/docs/) or [asyncpg](https://github.com/MagicStack/asyncpg), blog post [here](https://magic.io/blog/asyncpg-1m-rows-from-postgres-to-python/))
* Secure handling of secrets
* As the code grows, similar functions can be organized into modules to separate concerns.
* Better monitoring and metrics, for example: detecting which URL calls are taking too long, which content are taking too much space in the DBs.
* Practical implementations, for example booking an appointment for local authorities in Berlin, or price alarm for your favorite shopping website.
* Extra headers or authorizations for the URL requests

### Company's evaluation Criteria

* Please keep the code simple and understandable. Anything unnecessarily complex, undocumented or untestable will be considered a minus.
* Main design goal is maintainability.
* The solution
  * Must work (we need to be able to run the solution)
  * Must be tested and have tests
  * Must handle errors.
  * Should be production quality.
  * Should work for at least some thousands of separate sites (no need to provide proof of this).
  * Note! If something is not implemented in a way that meets these requirements e.g. due to time constraints, explicitly state these shortcomings and explain what would be the correct way of implementing it.

* Code formatting and clarity: “Programs must be written for people to read, and only incidentally for machines to execute.” (Harold Abelson, Structure and Interpretation of Computer Programs)
* Attribution. If you take code from Google results, examples etc., add attributions. We all know new things are often written based on search results.
* Continuous Integration is not evaluated.