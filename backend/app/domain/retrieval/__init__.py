# SERVICE-BOUNDARY: retrieval — v2 extraction point.
# In a multi-service architecture, this module would become the "Retrieval Service"
# responsible for hybrid search (FTS + pgvector), RRF ranking, and context budgeting.
# Seam: REST API + shared read replica; cache invalidation via event bus.

"""Retrieval domain — keyword, semantic, and hybrid search with context budgeting."""
