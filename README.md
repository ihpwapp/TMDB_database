## 🎬 TMDB Database Schema + Ingestion

A PostgreSQL schema and Python ingestion script for **The Movie Database (TMDB)** API.

## 📊 Schema Diagram

![TMDB Schema](schema/tmdb_schema.png)

## 🗂️ What's Included

- **16 tables** for Movies + People + Dimensions
- **SQL DDL** for PostgreSQL
- **Python ingestion** to populate from TMDB API

## 🚀 Quick Start

### 1. Setup Database

```bash
# Create database
createdb tmdb_db

# Run schema
psql -d tmdb_db -f schema/01_create_tables.sql

# Seed reference data
psql -d tmdb_db -f schema/02_seed_reference_data.sql
