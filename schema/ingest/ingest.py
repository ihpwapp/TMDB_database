"""
TMDB Ingestion Script
======================
Populates the PostgreSQL database with TMDB data.

Tables populated:
- genres
- movies
- people (actors, directors, crew)
- movie_cast
- movie_crew
- movie_genres
- movie_keywords
- movie_companies
- collections
- production_companies
- production_countries
- spoken_languages
- release_dates

Usage:
    python ingest/ingest.py
"""

import sys
from datetime import datetime
from utils import tmdb_request, rate_limit, execute_query, execute_batch


# =============================================
# HELPER: Progress tracking
# =============================================

def log(msg):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# =============================================
# INGEST: Genres
# =============================================

def ingest_genres():
    """Fetch and store all movie genres."""
    log("Fetching genres...")
    data = tmdb_request("/genre/movie/list", {"language": "en-US"})
    genres = data.get("genres", [])

    if not genres:
        log("  No genres found.")
        return

    rows = [(g["id"], g["name"]) for g in genres]
    query = """
        INSERT INTO genres (genre_id, name)
        VALUES %s
        ON CONFLICT (genre_id) DO UPDATE SET name = EXCLUDED.name
    """
    execute_batch(query, rows)
    log(f"  ✓ Inserted/updated {len(rows)} genres")


# =============================================
# INGEST: Movies (main loop)
# =============================================

def ingest_movies(max_pages=500):
    """
    Fetch popular movies across multiple pages,
    then fetch full details for each movie.
    """
    log(f"Fetching movie list (up to {max_pages} pages)...")
    movie_ids = []

    for page in range(1, max_pages + 1):
        data = tmdb_request("/movie/popular", {"page": page, "language": "en-US"})
        results = data.get("results", [])
        if not results:
            break
        movie_ids.extend([m["id"] for m in results])
        if page % 10 == 0:
            log(f"  Page {page}: collected {len(movie_ids)} movie IDs")
        rate_limit()

    log(f"  ✓ Found {len(movie_ids)} movies. Now fetching details...")

    # Fetch full details for each movie
    for i, movie_id in enumerate(movie_ids, 1):
        try:
            ingest_movie_details(movie_id)
            if i % 50 == 0:
                log(f"  Processed {i}/{len(movie_ids)} movies")
        except Exception as e:
            log(f"  ✗ Error on movie {movie_id}: {e}")
        rate_limit()

    log(f"  ✓ Completed movie ingestion")


def ingest_movie_details(movie_id):
    """
    Fetch full details for a single movie and insert into all related tables.
    Uses append_to_response to minimize API calls.
    """
    # Fetch movie + credits + keywords + release_dates + videos + images
    data = tmdb_request(
        f"/movie/{movie_id}",
        {
            "append_to_response": "credits,keywords,release_dates",
            "language": "en-US",
        }
    )

    # ----- 1. Insert movie -----
    insert_movie(data)

    # ----- 2. Insert collection (if any) -----
    collection = data.get("belongs_to_collection")
    if collection:
        insert_collection(collection)

    # ----- 3. Insert people (cast + crew) -----
    credits = data.get("credits", {})
    for person in credits.get("cast", []):
        insert_person(person)
    for person in credits.get("crew", []):
        insert_person(person)

    # ----- 4. Insert junction tables -----
    insert_movie_genres(movie_id, data.get("genres", []))
    insert_movie_keywords(movie_id, data.get("keywords", {}).get("keywords", []))
    insert_movie_companies(movie_id, data.get("production_companies", []))
    insert_movie_cast(movie_id, credits.get("cast", []))
    insert_movie_crew(movie_id, credits.get("crew", []))
    insert_production_countries(movie_id, data.get("production_countries", []))
    insert_spoken_languages(movie_id, data.get("spoken_languages", []))
    insert_release_dates(movie_id, data.get("release_dates", {}).get("results", []))


# =============================================
# INSERT HELPERS
# =============================================

def insert_movie(data):
    """Insert or update a single movie."""
    belongs_to_collection_id = (
        data.get("belongs_to_collection", {}).get("id")
        if data.get("belongs_to_collection")
        else None
    )

    query = """
        INSERT INTO movies (
            movie_id, imdb_id, title, original_title, tagline, overview,
            release_date, status, runtime, budget, revenue,
            popularity, vote_average, vote_count, adult, video,
            homepage, poster_path, backdrop_path, original_language,
            belongs_to_collection_id, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (movie_id) DO UPDATE SET
            title = EXCLUDED.title,
            budget = EXCLUDED.budget,
            revenue = EXCLUDED.revenue,
            popularity = EXCLUDED.popularity,
            vote_average = EXCLUDED.vote_average,
            vote_count = EXCLUDED.vote_count,
            updated_at = CURRENT_TIMESTAMP
    """

    params = (
        data.get("id"),
        data.get("imdb_id"),
        data.get("title"),
        data.get("original_title"),
        data.get("tagline"),
        data.get("overview"),
        data.get("release_date") or None,
        data.get("status"),
        data.get("runtime"),
        data.get("budget", 0),
        data.get("revenue", 0),
        data.get("popularity"),
        data.get("vote_average"),
        data.get("vote_count"),
        data.get("adult", False),
        data.get("video", False),
        data.get("homepage"),
        data.get("poster_path"),
        data.get("backdrop_path"),
        data.get("original_language"),
        belongs_to_collection_id,
    )
    execute_query(query, params)


def insert_collection(collection):
    """Insert or update a collection."""
    query = """
        INSERT INTO collections (collection_id, name, overview, poster_path, backdrop_path)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (collection_id) DO UPDATE SET
            name = EXCLUDED.name,
            overview = EXCLUDED.overview
    """
    execute_query(query, (
        collection.get("id"),
        collection.get("name"),
        collection.get("overview"),
        collection.get("poster_path"),
        collection.get("backdrop_path"),
    ))


def insert_person(person):
    """Insert or update a person (actor/director/crew)."""
    query = """
        INSERT INTO people (
            person_id, name, gender, known_for_department,
            popularity, profile_path, adult
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (person_id) DO UPDATE SET
            name = EXCLUDED.name,
            popularity = EXCLUDED.popularity
    """
    execute_query(query, (
        person.get("id"),
        person.get("name"),
        person.get("gender"),
        person.get("known_for_department"),
        person.get("popularity"),
        person.get("profile_path"),
        person.get("adult", False),
    ))


def insert_movie_genres(movie_id, genres):
    """Insert movie-genre relationships."""
    if not genres:
        return
    rows = [(movie_id, g["id"]) for g in genres]
    query = """
        INSERT INTO movie_genres (movie_id, genre_id)
        VALUES %s
        ON CONFLICT DO NOTHING
    """
    execute_batch(query, rows)


def insert_movie_keywords(movie_id, keywords):
    """Insert keywords and movie-keyword relationships."""
    if not keywords:
        return

    # First, insert keywords themselves
    kw_rows = [(k["id"], k["name"]) for k in keywords]
    execute_batch(
        """
        INSERT INTO keywords (keyword_id, name)
        VALUES %s
        ON CONFLICT (keyword_id) DO UPDATE SET name = EXCLUDED.name
        """,
        kw_rows
    )

    # Then, link them to the movie
    mk_rows = [(movie_id, k["id"]) for k in keywords]
    execute_batch(
        """
        INSERT INTO movie_keywords (movie_id, keyword_id)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        mk_rows
    )


def insert_movie_companies(movie_id, companies):
    """Insert companies and movie-company relationships."""
    if not companies:
        return

    # Insert companies
    comp_rows = [
        (
            c.get("id"),
            c.get("name"),
            c.get("origin_country"),
        )
        for c in companies
    ]
    execute_batch(
        """
        INSERT INTO production_companies (company_id, name, origin_country)
        VALUES %s
        ON CONFLICT (company_id) DO UPDATE SET name = EXCLUDED.name
        """,
        comp_rows
    )

    # Link to movie
    mc_rows = [(movie_id, c["id"]) for c in companies if c.get("id")]
    execute_batch(
        """
        INSERT INTO movie_companies (movie_id, company_id)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        mc_rows
    )


def insert_movie_cast(movie_id, cast):
    """Insert movie cast relationships."""
    if not cast:
        return
    rows = [
        (c.get("credit_id"), movie_id, c.get("id"), c.get("character"), c.get("order"), c.get("gender"))
        for c in cast if c.get("credit_id") and c.get("id")
    ]
    if not rows:
        return
    execute_batch(
        """
        INSERT INTO movie_cast (credit_id, movie_id, person_id, character, cast_order, gender)
        VALUES %s
        ON CONFLICT (credit_id) DO NOTHING
        """,
        rows
    )


def insert_movie_crew(movie_id, crew):
    """Insert movie crew relationships."""
    if not crew:
        return
    rows = [
        (c.get("credit_id"), movie_id, c.get("id"), c.get("department"), c.get("job"))
        for c in crew if c.get("credit_id") and c.get("id")
    ]
    if not rows:
        return
    execute_batch(
        """
        INSERT INTO movie_crew (credit_id, movie_id, person_id, department, job)
        VALUES %s
        ON CONFLICT (credit_id) DO NOTHING
        """,
        rows
    )


def insert_production_countries(movie_id, countries):
    """Insert movie production countries."""
    if not countries:
        return
    rows = [(movie_id, c.get("iso_3166_1"), c.get("name")) for c in countries if c.get("iso_3166_1")]
    if not rows:
        return
    execute_batch(
        """
        INSERT INTO production_countries (movie_id, iso_3166_1, name)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        rows
    )


def insert_spoken_languages(movie_id, languages):
    """Insert movie spoken languages."""
    if not languages:
        return
    rows = [(movie_id, l.get("iso_639_1"), l.get("name")) for l in languages if l.get("iso_639_1")]
    if not rows:
        return
    execute_batch(
        """
        INSERT INTO spoken_languages (movie_id, iso_639_1, name)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        rows
    )


def insert_release_dates(movie_id, releases):
    """Insert movie release dates."""
    if not releases:
        return
    rows = [
        (
            movie_id,
            r.get("iso_3166_1"),
            r.get("certification"),
            r.get("release_date"),
            r.get("type"),
            r.get("note"),
        )
        for r in releases if r.get("iso_3166_1")
    ]
    if not rows:
        return
    # Delete existing releases for this movie first (to avoid duplicates on re-runs)
    execute_query("DELETE FROM release_dates WHERE movie_id = %s", (movie_id,))
    execute_batch(
        """
        INSERT INTO release_dates (movie_id, iso_3166_1, certification, release_date, type, note)
        VALUES %s
        """,
        rows
    )


# =============================================
# MAIN
# =============================================

def main():
    """Run the full ingestion pipeline."""
    log("=" * 50)
    log("🎬 TMDB Ingestion Starting")
    log("=" * 50)

    try:
        # Step 1: Genres (required before movies)
        ingest_genres()

        # Step 2: Movies (fetches everything else)
        ingest_movies(max_pages=500)

        log("=" * 50)
        log("✅ Ingestion completed successfully!")
        log("=" * 50)

    except KeyboardInterrupt:
        log("\n⚠️  Ingestion interrupted by user.")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
