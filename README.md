# 🎬 TMDB Ingestion Pipeline


**[Data Dictionary (Google Docs)](https://docs.google.com/document/d/1CV-DElvKOjLBfyKnuJ3P1iOLmUA4N8z4Qms3wYUiUXs/edit?usp=sharing)** — Contains definitions, data types, and core schemas for this project.


A PostgreSQL schema and Python ingestion script for **The Movie Database (TMDB)** API.
=======
This repository provides a PostgreSQL schema and Python-based ingestion pipeline to populate a local PostgreSQL database with metadata from The Movie Database (TMDB) API.


**Contents (high level)**
- Database schema and seed: [schema/01_create_tables.sql](schema/01_create_tables.sql) and [schema/02_schema_seed_reference_data.sql](schema/02_schema_seed_reference_data.sql)
- Ingestion scripts: [ingest/ingest.py](ingest/ingest.py) and [ingest/enrich_people.py](ingest/enrich_people.py)
- Utilities: [ingest/utils.py](ingest/utils.py)
- Python dependencies: [requirements.txt](requirements.txt)

## **Schema Diagram**

![TMDB Schema](schema/tmdb_schema.png)

## **Quick Start**

1) Create a Python virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2) Prepare the PostgreSQL database

```bash
# Create the database (adjust name as needed)
createdb tmdb_db

# Create tables
psql -d tmdb_db -f schema/01_create_tables.sql

# Seed reference data (countries, languages, genres)
psql -d tmdb_db -f schema/02_schema_seed_reference_data.sql
```

3) Configure environment variables

Create a `.env` file in the project root (not checked in) with at least the following variables:

- `TMDB_API_KEY` — your TMDB API key
- `DB_HOST` — database host (default: `localhost`)
- `DB_PORT` — database port (default: `5432`)
- `DB_NAME` — database name (default: `tmdb_db`)
- `DB_USER` — database user (default: `postgres`)
- `DB_PASSWORD` — database password
- `INGEST_PAGES` — pages to fetch per source (optional, default in code: 500)
- `INGEST_DELAY` — seconds between API calls (optional, default in code)

Example `.env`:

```env
TMDB_API_KEY=your_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tmdb_db
DB_USER=postgres
DB_PASSWORD=secret
INGEST_PAGES=200
INGEST_DELAY=0.1
```

4) Run the full ingestion pipeline

```bash
python -m ingest.ingest
```

This will:
- Fetch genres first (required)
- Collect movie IDs from `/movie/popular` and `/discover/movie` (by revenue)
- Fetch full movie details using `append_to_response=credits,keywords,release_dates`
- Insert/update movies, people, collections, keywords, companies, junction tables, release dates, and other related data

5) Enrich people details (optional)

```bash
python -m ingest.enrich_people
```

This script updates `people` rows that are missing extended fields (biography, birthday, place_of_birth, imdb_id, homepage, etc.).

## **Repository Structure**

- [requirements.txt](requirements.txt) — Python dependencies
- [ingest/ingest.py](ingest/ingest.py) — main ingestion pipeline and DB insert helpers
- [ingest/enrich_people.py](ingest/enrich_people.py) — separate enrichment pass for people details
- [ingest/utils.py](ingest/utils.py) — TMDB API helpers and DB helpers (connection, execute_batch, rate limiting)
- [schema/01_create_tables.sql](schema/01_create_tables.sql) — DDL for PostgreSQL
- [schema/02_schema_seed_reference_data.sql](schema/02_schema_seed_reference_data.sql) — reference data seeds (countries, languages, genres)
- [ERD/](ERD/) — Entity Relationship Diagrams (ignored in README per request)

## **Implementation Notes**

- The ingestion code uses `requests` to call TMDB and `psycopg2` / `execute_values` for efficient batch inserts.
- The pipeline is defensive: main movie insert is considered critical — failures there skip dependent inserts for that movie, while other parts use try/except and continue.
- Rate limiting is configurable via `INGEST_DELAY` to avoid hitting TMDB rate limits.

## **Environment & Dependencies**

- See [requirements.txt](requirements.txt) for packages (requests, python-dotenv, psycopg2-binary, sqlalchemy, pandas, numpy, loguru, etc.).

## **Database Schema**

Run `schema/01_create_tables.sql` to create the primary tables. The schema includes core entities (`movies`, `people`, `collections`, `production_companies`), reference tables (`countries`, `languages`, `genres`, `keywords`) and junction tables for many-to-many relationships.

If you need to inspect or edit the schema, see the files in the `schema/` directory.

## **Troubleshooting**

- If ingestion fails with DB connection errors, verify your `.env` DB_* variables and that PostgreSQL is running and accessible.
- If TMDB requests fail, confirm `TMDB_API_KEY` is set and valid, and consider increasing `INGEST_DELAY`.
- For performance, reduce `INGEST_PAGES` during development.

\
## **Detailed Script Descriptions**

**ingest/ingest.py** (primary)

- **Purpose:** Full ingestion pipeline that collects movie IDs from TMDB, fetches detailed movie data (including credits, keywords, and release dates), and writes normalized rows into PostgreSQL.
- **Configuration:** Reads environment variables from `.env` (see above). Important runtime controls: `INGEST_PAGES` (how many pages to request per source) and `INGEST_DELAY` (seconds to sleep between API calls to avoid rate limits).
- **High-level flow:**
	- `main()` — orchestrates the run: logs startup, runs `ingest_genres()` then `ingest_movies()`, and handles KeyboardInterrupt / fatal errors.
	- `ingest_genres()` — fetches `/genre/movie/list` and upserts into the `genres` table using batch inserts.
	- `ingest_movies()` — two-source collection of movie IDs:
		1. `/movie/popular` (paginated)
		2. `/discover/movie` (sorted by revenue, paginated)
		IDs are combined into a set to deduplicate before detail fetch.
	- For each movie ID, `ingest_movie_details(movie_id)` is called to fetch the full movie payload with `append_to_response=credits,keywords,release_dates` and insert related records.
- **Important helper functions (what they do):**
	- `tmdb_request(endpoint, params)` (from `ingest/utils.py`) — performs requests to TMDB and injects `api_key`.
	- `rate_limit()` — sleeps for `INGEST_DELAY` between calls.
	- `execute_query()` / `execute_batch()` — DB helpers that run single queries or efficient `execute_values` batch inserts (transactional, with rollback on error).
	- `insert_movie(data)` — upserts the core row into `movies`. This is treated as the critical insert for a movie; if it fails, dependent inserts are skipped for that movie.
	- `insert_collection(collection)` — upserts collections into `collections`.
	- `insert_person(person)` — upserts people into `people` (used for cast & crew).
	- `insert_movie_genres`, `insert_movie_keywords`, `insert_movie_companies`, `insert_movie_cast`, `insert_movie_crew`, `insert_production_countries`, `insert_spoken_languages`, `insert_release_dates` — insert junctions and related tables; many use batch inserts and `ON CONFLICT DO NOTHING` for idempotency.
- **DB semantics & idempotency:**
	- Uses `ON CONFLICT` upserts for stable re-runs.
	- Batch inserts via `psycopg2.extras.execute_values` for performance.
	- `insert_release_dates` deletes existing rows for a movie before re-inserting to avoid duplicate release entries.
- **Error handling & resilience:**
	- The pipeline logs progress and wraps many non-critical inserts in try/except so a single failure (e.g., a bad keyword or company payload) does not stop the whole run.
	- The core `insert_movie` is considered critical; failures there skip dependent inserts for that movie to avoid orphaned junction rows.
- **Performance & tuning:**
	- Reduce `INGEST_PAGES` for faster testing; increase or decrease `INGEST_DELAY` to balance speed with API limits.
	- Because movie detail fetches are per-movie and numerous, total runtime can be many hours for large `INGEST_PAGES` values.

**ingest/enrich_people.py** (secondary)

- **Purpose:** One-off enrichment pass that fetches full person details from TMDB for `people` rows that lack extended fields and updates the DB.
- **Flow:**
	- `get_people_to_enrich()` selects `person_id` values from `people` where `biography IS NULL`, ordered by popularity and limited to a batch (5000 by default).
	- `enrich_person(person_id)` calls `/person/{id}` and issues an `UPDATE people SET ... WHERE person_id = %s` to populate `biography`, `birthday`, `deathday`, `place_of_birth`, `imdb_id`, `homepage`, and preserve/COALESCE other fields.
	- The script iterates through the list, calling `rate_limit()` between requests and logging progress, with simple retry/failure handling per-person.

**Where to look in code**
- See the orchestration and logging in `[ingest/ingest.py](ingest/ingest.py)`
- See API + DB helpers in `[ingest/utils.py](ingest/utils.py)`
- See people enrichment details in `[ingest/enrich_people.py](ingest/enrich_people.py)`

