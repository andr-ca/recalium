"""Import domain — normalize AI-assistant conversation exports.

Decomposes a ChatGPT or Claude export into individual conversations so each one
flows through the processing pipeline (summarize → extract → link) with its own
provenance, instead of being stored as a single opaque multi-conversation blob.
"""
