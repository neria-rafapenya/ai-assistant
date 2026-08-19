from typing import Any
from urllib.parse import unquote_plus

from app.main import ProcessDocumentRequest, process_document


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process PDF objects from an S3 ObjectCreated notification.

    Exceptions intentionally propagate so Lambda can retry the event or send
    it to a dead-letter destination once SQS is introduced.
    """
    processed: list[dict[str, Any]] = []

    for record in event.get("Records", []):
        raw_key = record.get("s3", {}).get("object", {}).get("key")
        if not raw_key:
            continue
        key = unquote_plus(raw_key)
        if not key.startswith("incoming/") or not key.lower().endswith(".pdf"):
            continue
        result = process_document(ProcessDocumentRequest(key=key))
        processed.append(result.model_dump())

    return {"processed": processed}
