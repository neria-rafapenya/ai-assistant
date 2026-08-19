# Backend

Initial FastAPI service.

The chat supports two providers:

- `simulated`: provider local, sin coste, usado por defecto.
- `bedrock`: Amazon Bedrock, facturado por uso al invocar el modelo.

El proveedor por defecto se configura con `AI_PROVIDER`. También se puede
seleccionar `bedrock` para una única petición enviando el campo opcional
`provider`, lo que permite hacer una prueba controlada sin cambiar la
configuración global.

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

### Prueba controlada de Bedrock

Configura primero `BEDROCK_MODEL_ID` en `.env` y conserva
`AI_PROVIDER=simulated`. Después envía:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"message":"Responde brevemente: ¿qué es un API?", "provider":"bedrock"}'
```

La llamada solo tendrá coste si el proveedor Bedrock llega a invocarse.
