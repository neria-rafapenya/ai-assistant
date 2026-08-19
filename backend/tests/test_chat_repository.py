from app.chat_repository import SQLiteChatRepository


def test_sqlite_chat_repository_persists_messages(tmp_path) -> None:
    repository = SQLiteChatRepository(tmp_path / "chat.db")

    repository.save_message("session-1", "user", "hola")
    repository.save_message(
        "session-1",
        "assistant",
        "respuesta",
        provider="simulated",
        route="general",
        sources=[],
    )

    messages = repository.list_messages("session-1")

    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "respuesta"
    assert messages[1]["provider"] == "simulated"
