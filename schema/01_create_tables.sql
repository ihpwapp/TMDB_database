-- =============================================
-- 🎬 TMDB Database Schema - PostgreSQL
-- =============================================
-- Movies Only (Phase 1): 16 tables
-- =============================================

DROP TABLE IF EXISTS release_dates CASCADE;
DROP TABLE IF EXISTS spoken_languages CASCADE;
DROP TABLE IF EXISTS production_countries CASCADE;
DROP TABLE IF EXISTS movie_companies CASCADE;
DROP TABLE IF EXISTS movie_keywords CASCADE;
DROP TABLE IF EXISTS movie_genres CASCADE;
DROP TABLE IF EXISTS movie_crew CASCADE;
DROP TABLE IF EXISTS movie_cast CASCADE;
DROP TABLE IF EXISTS movies CASCADE;
DROP TABLE IF EXISTS people CASCADE;
DROP TABLE IF EXISTS production_companies CASCADE;
DROP TABLE IF EXISTS collections CASCADE;
DROP TABLE IF EXISTS keywords CASCADE;
DROP TABLE IF EXISTS genres CASCADE;
DROP TABLE IF EXISTS languages CASCADE;
DROP TABLE IF EXISTS countries CASCADE;

-- =============================================
-- ⚙️ REFERENCE DATA
-- =============================================

CREATE TABLE countries (
    iso_3166_1   VARCHAR(2) PRIMARY KEY,
    english_name VARCHAR(100),
    native_name  VARCHAR(100)
);

CREATE TABLE languages (
    iso_639_1    VARCHAR(2) PRIMARY KEY,
    english_name VARCHAR(100),
    name         VARCHAR(100)
);

-- =============================================
-- 🏷️ SHARED DIMENSIONS
-- =============================================

CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY,
    name     VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE keywords (
    keyword_id INTEGER PRIMARY KEY,
    name       VARCHAR(255) NOT NULL
);

CREATE INDEX idx_keywords_name ON keywords(name);

CREATE TABLE collections (
    collection_id INTEGER PRIMARY KEY,
    name          VARCHAR(255),
    overview      TEXT,
    poster_path   VARCHAR(255),
    backdrop_path VARCHAR(255)
);

CREATE TABLE production_companies (
    company_id      INTEGER PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    headquarters    VARCHAR(255),
    homepage        VARCHAR(500),
    logo_path       VARCHAR(255),
    origin_country  VARCHAR(2) REFERENCES countries(iso_3166_1),
    parent_company  VARCHAR(255)
);

CREATE INDEX idx_companies_name ON production_companies(name);

-- =============================================
-- 👥 CORE ENTITIES
-- =============================================

CREATE TABLE people (
    person_id             INTEGER PRIMARY KEY,
    name                  VARCHAR(255) NOT NULL,
    gender                INTEGER,
    known_for_department  VARCHAR(100),
    biography             TEXT,
    birthday              DATE,
    deathday              DATE,
    place_of_birth        VARCHAR(255),
    popularity            DECIMAL(10,3),
    profile_path          VARCHAR(255),
    imdb_id               VARCHAR(20),
    homepage              VARCHAR(500),
    adult                 BOOLEAN DEFAULT FALSE,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_people_name ON people(name);
CREATE INDEX idx_people_popularity ON people(popularity);

CREATE TABLE movies (
    movie_id                  INTEGER PRIMARY KEY,
    imdb_id                   VARCHAR(20),
    title                     VARCHAR(500) NOT NULL,
    original_title            VARCHAR(500),
    tagline                   VARCHAR(1000),
    overview                  TEXT,
    release_date              DATE,
    status                    VARCHAR(50),
    runtime                   INTEGER,
    budget                    BIGINT,
    revenue                   BIGINT,
    popularity                DECIMAL(10,3),
    vote_average              DECIMAL(3,1),
    vote_count                INTEGER,
    adult                     BOOLEAN DEFAULT FALSE,
    video                     BOOLEAN DEFAULT FALSE,
    homepage                  VARCHAR(500),
    poster_path               VARCHAR(255),
    backdrop_path             VARCHAR(255),
    original_language         VARCHAR(10),
    belongs_to_collection_id  INTEGER REFERENCES collections(collection_id),
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_release_date ON movies(release_date);
CREATE INDEX idx_movies_budget ON movies(budget);
CREATE INDEX idx_movies_revenue ON movies(revenue);
CREATE INDEX idx_movies_popularity ON movies(popularity);
CREATE INDEX idx_movies_collection ON movies(belongs_to_collection_id);

-- =============================================
-- 🔗 MOVIE JUNCTIONS
-- =============================================

CREATE TABLE movie_cast (
    credit_id   VARCHAR(50) PRIMARY KEY,
    movie_id    INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    person_id   INTEGER NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    character   VARCHAR(500),
    cast_order  INTEGER,
    gender      INTEGER
);

CREATE INDEX idx_movie_cast_movie ON movie_cast(movie_id);
CREATE INDEX idx_movie_cast_person ON movie_cast(person_id);

CREATE TABLE movie_crew (
    credit_id   VARCHAR(50) PRIMARY KEY,
    movie_id    INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    person_id   INTEGER NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    department  VARCHAR(100),
    job         VARCHAR(255)
);

CREATE INDEX idx_movie_crew_movie ON movie_crew(movie_id);
CREATE INDEX idx_movie_crew_person ON movie_crew(person_id);
CREATE INDEX idx_movie_crew_job ON movie_crew(job);

CREATE TABLE movie_genres (
    movie_id  INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    genre_id  INTEGER NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

CREATE TABLE movie_keywords (
    movie_id    INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    keyword_id  INTEGER NOT NULL REFERENCES keywords(keyword_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, keyword_id)
);

CREATE TABLE movie_companies (
    movie_id   INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES production_companies(company_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, company_id)
);

CREATE TABLE production_countries (
    movie_id    INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    iso_3166_1  VARCHAR(2) NOT NULL REFERENCES countries(iso_3166_1),
    name        VARCHAR(100),
    PRIMARY KEY (movie_id, iso_3166_1)
);

CREATE TABLE spoken_languages (
    movie_id    INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    iso_639_1   VARCHAR(2) NOT NULL REFERENCES languages(iso_639_1),
    name        VARCHAR(100),
    PRIMARY KEY (movie_id, iso_639_1)
);

-- =============================================
-- 📅 RELEASE DATES
-- =============================================

CREATE TABLE release_dates (
    id             SERIAL PRIMARY KEY,
    movie_id       INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    iso_3166_1     VARCHAR(2) NOT NULL REFERENCES countries(iso_3166_1),
    certification  VARCHAR(20),
    release_date   DATE,
    type           INTEGER,
    note           VARCHAR(500)
);

CREATE INDEX idx_release_movie ON release_dates(movie_id);
CREATE INDEX idx_release_date ON release_dates(release_date);

-- =============================================
-- ✅ DONE
-- =============================================
SELECT 'Schema created: ' || COUNT(*) || ' tables' AS status
FROM information_schema.tables 
WHERE table_schema = 'public';
