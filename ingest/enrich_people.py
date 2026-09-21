import os
import sys
from datetime import datetime
from dotenv import load_dotenv

from ingest.utils import tmdb_request, rate_limit, execute_query

load_dotenv()

INGEST_DELAY = float(os.getenv("INGEST_DELAY", "0.25"))


def log(msg):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def get_people_to_enrich():
    """Get list of people IDs that need enrichment."""
    query = """
        SELECT person_id FROM people 
WHERE biography IS NULL
ORDER BY popularity DESC NULLS LAST
LIMIT 5000;
    """
    rows = execute_query(query, fetch=True)
    return [row[0] for row in rows]


def enrich_person(person_id):
    """Fetch full details for a person and update the database."""
    try:
        data = tmdb_request(f"/person/{person_id}")
    except Exception as e:
        log(f"  ✗ Failed to fetch person {person_id}: {e}")
        return False
    
    # Update with full info
    query = """
        UPDATE people SET
            biography = %s,
            birthday = %s,
            deathday = %s,
            place_of_birth = %s,
            imdb_id = %s,
            homepage = %s,
            gender = COALESCE(%s, gender),
            known_for_department = COALESCE(%s, known_for_department)
        WHERE person_id = %s
    """
    
    execute_query(query, (
        data.get("biography"),
        data.get("birthday"),
        data.get("deathday"),
        data.get("place_of_birth"),
        data.get("imdb_id"),
        data.get("homepage"),
        data.get("gender"),
        data.get("known_for_department"),
        person_id
    ))
    
    return True


def main():
    """Enrich all people missing detailed info."""
    log("=" * 50)
    log("👥 Enriching People Data")
    log("=" * 50)
    
    # Get list of people to enrich
    person_ids = get_people_to_enrich()
    total = len(person_ids)
    
    log(f"   Found {total} people to enrich")
    log(f"   Estimated time: ~{int(total * INGEST_DELAY / 60)} minutes")
    
    if total == 0:
        log("✅ Nothing to enrich!")
        return
    
    log("=" * 50)
    
    # Process each person
    success_count = 0
    fail_count = 0
    
    for i, person_id in enumerate(person_ids, 1):
        if enrich_person(person_id):
            success_count += 1
        else:
            fail_count += 1
        
        # Progress logging
        if i % 50 == 0:
            log(f"  Progress: {i}/{total} ({success_count} ok, {fail_count} failed)")
        
        rate_limit()
    
    log("=" * 50)
    log(f"✅ Done! Enriched {success_count}/{total} people ({fail_count} failed)")
    log("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️  Enrichment interrupted by user.")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ Enrichment failed: {e}")
        sys.exit(1)
