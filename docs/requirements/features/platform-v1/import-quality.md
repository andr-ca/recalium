# Import Data Quality

## Purpose
The cold-start strategy depends on import quality. Real-world AI conversation exports are messy, and the import experience is the single biggest factor in whether the first-run "aha moment" occurs.

## ChatGPT export realities
- Exports contain system messages, tool calls, image generation prompts, code interpreter output, browsing results, and plugin artifacts alongside conversation text.
- Many conversations are trivial (one-shot questions, "hello" tests, abandoned threads).
- Conversation titles are often auto-generated and meaningless.
- No session or project grouping exists in the export format.
- Conversations may contain mixed languages.
- Code blocks, error messages, and stack traces may dominate some conversations.
- Some conversations contain sensitive personal information the user may not remember sharing.

## Claude export realities
- Export format includes conversation metadata and message content.
- Conversations may include artifact content (code, documents) that is structurally distinct from chat messages.
- Project-scoped conversations may have associated project context that is not included in the export.
- System prompts and custom instructions are not typically included.

## Generic and plain text imports
- No guaranteed structure or metadata.
- Source system, timestamps, and session boundaries must be inferred or declared by the user.
- Markdown files may contain mixed content types with no clear conversation boundaries.

## Requirements

### Import preview and filtering
- Import must support previewing before full processing: conversation count, estimated token volume, estimated processing cost, and distribution by length and date.
- Import must support filtering or triaging before full processing: skip conversations shorter than a configurable turn count or character count threshold.
- Trivial conversations (below the configured threshold) should be archived but not processed by default, to reduce noise and cost.
- The user must be able to override the trivial-conversation filter and force processing of all imported conversations.

### Content handling
- Import must handle non-text content gracefully: code blocks preserved as-is, image references noted, tool output included or excluded by user preference.
- System messages, tool calls, and plugin artifacts must be distinguishable from user and assistant messages in the archive.
- Import must preserve conversation boundaries, turn order, and role attribution (user vs. assistant vs. system).

### Error handling
- The system must handle malformed or incomplete export files without crashing or silently dropping conversations.
- If individual conversations within a batch import fail validation, the system must continue processing valid conversations and report failures clearly.
- Partial imports must be resumable: the user can fix or skip failed items and continue without re-importing already-processed conversations.

### Sensitivity handling during import
- Bulk imports must pass through the same sensitivity pre-classification gate as individual ingestion.
- The import preview should flag conversations that contain potentially sensitive content based on local pre-classification.
- The user must be able to exclude flagged conversations from provider-backed processing before confirming the import.

### Quality indicators
- After import and processing complete, the system should display a quality summary: total conversations imported, total facts extracted, extraction coverage (conversations that yielded at least one fact vs. total), and any conversations that produced zero useful output.
- If more than 50% of imported conversations produce zero extractable facts, the system should surface this as a quality warning rather than silently proceeding.
