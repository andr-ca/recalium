# SERVICE-BOUNDARY: backup — v2 extraction point.
# In a multi-service architecture, this module would become the "Backup Service"
# responsible for pg_dump scheduling, retention policy, and restore orchestration.
# Seam: REST API; requires direct PostgreSQL access (stays co-located with DB in v2).
