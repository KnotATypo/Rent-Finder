# Rent Finder

Application to scrape rental listings and serve them in a mobile-friendly format to be easily processed.

## Prerequisites

- Python 3.14
- PostgreSQL
- S3 compatible datastore (MinIO recommend)
- Chrome/Chromium browser

Setting up these requirements is outside the scope of this project. However, if you intend to use Docker to run the
project, PostgreSQL and MinIO are easily configured to also run in Docker.

## Configuration

To configure the application, create a `.env` file in the root directory of the project if running standalone or
alongside the appropriate docker-compose file.

This file can be created by copying/renaming the `.env-template` file or copying the below example.

```dotenv
GEOCODE_API_KEY=

DB_USER=
DB_PASS=
DB_HOST=

S3_ENDPOINT_URL=
S3_KEY_ID=
S3_ACCESS_KEY=
```

- `GEOCODE_API_KEY` - API key for https://geocode.maps.co/
- `DB_*` - Details for PostgreSQL database
- `S3_*` - Details for S3 compatible datastore

## Running

The intended way to run the application is through a Docker container which can be pulled from `knotatypo/rent-finder`.
An example of a compose file can be found in this repo.

If running standalone, it can be run with the `uv run --env-file .env host` command. This will host the web application
and schedule the search task to be run daily. The search task can also be run manually with
`uv run --env-file .env search`.