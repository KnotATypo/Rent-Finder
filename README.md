# Rent Scraper

Application to scrape and track rental listings across Australia.

## Prerequisites

- Python 3.14
- PostgreSQL
- Chrome/Chromium browser

Setting up these requirements is outside the scope of this project. However, if you intend to use Docker to run the
project, PostgreSQL is easily configured to also run in Docker.

## Configuration

To configure the application, create a `.env` file in the root directory of the project if running standalone or
alongside the appropriate docker-compose file.

This file can be created by copying/renaming the `.env-template` file or copying the below example.

```dotenv
GEOCODE_API_KEY=

DB_USER=
DB_PASS=
DB_HOST=
```

- ~~`GEOCODE_API_KEY` - API key for https://geocode.maps.co/~~
- `DB_*` - Details for PostgreSQL database

Additionally, there are 2 optional environmental variables:

- `LOG_LEVEL` - Defaults to "INFO", but can be set to any standard logging level such as "DEBUG" or "WARN"
- `PROGRESS_BARS` - Set to any value to enable progress bars while searching. Disabled by default to allow for clearer
  logging

## Running

The intended way to run the application is through a Docker container which can be pulled from `knotatypo/rent-scraper`.
An example of a compose file can be found in this repo.

The search task can also be run manually with `uv run --env-file .env search`.