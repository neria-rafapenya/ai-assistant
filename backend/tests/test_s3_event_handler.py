from types import SimpleNamespace

from app import s3_event_handler


def test_lambda_handler_processes_pdf_s3_events(monkeypatch) -> None:
    calls = []

    def fake_process(payload):
        calls.append(payload.key)
        return SimpleNamespace(
            model_dump=lambda: {"status": "processed", "source_key": payload.key}
        )

    monkeypatch.setattr(s3_event_handler, "process_document", fake_process)
    result = s3_event_handler.lambda_handler(
        {
            "Records": [
                {"s3": {"object": {"key": "incoming%2Fdemo.pdf"}}},
                {"s3": {"object": {"key": "processed%2Fdemo.json"}}},
            ]
        },
        None,
    )

    assert calls == ["incoming/demo.pdf"]
    assert result == {
        "processed": [
            {"status": "processed", "source_key": "incoming/demo.pdf"}
        ]
    }


def test_lambda_handler_processes_sqs_wrapped_s3_events(monkeypatch) -> None:
    calls = []

    def fake_process(payload):
        calls.append(payload.key)
        return SimpleNamespace(
            model_dump=lambda: {"status": "processed", "source_key": payload.key}
        )

    monkeypatch.setattr(s3_event_handler, "process_document", fake_process)
    result = s3_event_handler.lambda_handler(
        {
            "Records": [
                {
                    "body": (
                        '{"Records":[{"s3":{"object":'
                        '{"key":"incoming%2Ffrom-sqs.pdf"}}}]}'
                    )
                }
            ]
        },
        None,
    )

    assert calls == ["incoming/from-sqs.pdf"]
    assert result == {
        "processed": [
            {"status": "processed", "source_key": "incoming/from-sqs.pdf"}
        ]
    }
