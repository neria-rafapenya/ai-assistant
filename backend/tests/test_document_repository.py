from app.document_repository import SQLiteDocumentRepository


def test_document_repository_tracks_processing_and_completion(tmp_path) -> None:
    repository = SQLiteDocumentRepository(tmp_path / "chat.db", max_attempts=2)
    assert repository.start_processing("incoming/test.pdf") is True
    repository.mark_completed("incoming/test.pdf", "processed/test.json", 3)
    document = repository.get("incoming/test.pdf")
    assert document["status"] == "processed"
    assert document["attempts"] == 1
    assert document["processed_key"] == "processed/test.json"
    assert document["chunks"] == 3


def test_document_repository_limits_attempts(tmp_path) -> None:
    repository = SQLiteDocumentRepository(tmp_path / "chat.db", max_attempts=1)
    assert repository.start_processing("incoming/test.pdf") is True
    repository.mark_failed("incoming/test.pdf", "failure")
    assert repository.start_processing("incoming/test.pdf") is False
