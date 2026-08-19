# Backend

Initial FastAPI service.

Current chat implementation uses a simulated local provider.
No Bedrock or external LLM calls are executed yet.

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Endpoints

- `GET /health`
- `POST /api/v1/chat`

### Example request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"message":"hola"}'
```

Example response:

```json
{
  "reply": "[simulado] Recibi: hola",
  "session_id": null,
  "provider": "simulated"
}
```
