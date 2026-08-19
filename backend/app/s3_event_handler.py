import json
from typing import Any, Iterator
from urllib.parse import unquote_plus

from app.main import ProcessDocumentRequest, process_document


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process PDF objects from direct S3 or SQS-wrapped S3 notifications.

    Exceptions intentionally propagate so Lambda can retry the event or send
    it to a dead-letter queue.
    """
    processed: list[dict[str, Any]] = []

    for record in _iter_s3_records(event):
        raw_key = record.get("s3", {}).get("object", {}).get("key")
        if not raw_key:
            continue
        key = unquote_plus(raw_key)
        if not key.startswith("incoming/") or not key.lower().endswith(".pdf"):
            continue
        result = process_document(ProcessDocumentRequest(key=key))
        processed.append(result.model_dump())

    return {"processed": processed}


def _iter_s3_records(event: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield S3 records from either a direct S3 event or an SQS event."""
    for record in event.get("Records", []):
        body = record.get("body")
        if body is None:
            yield record
            continue

        nested_event = json.loads(body) if isinstance(body, str) else body
        yield from nested_event.get("Records", [])
