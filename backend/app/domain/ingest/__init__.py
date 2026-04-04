# SERVICE-BOUNDARY: ingest — v2 extraction point.
# In a multi-service architecture, this module would become the "Ingest Service"
# responsible for parsing, deduplication, and raw archive persistence.
# Seam: REST API + async job queue (currently in-process PostgreSQL SKIP LOCKED).

"""Ingest domain — validate, parse, persist, and enqueue."""
