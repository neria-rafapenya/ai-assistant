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

Configura `BEDROCK_MODEL_ID=eu.amazon.nova-lite-v1:0` en `.env` y conserva
`AI_PROVIDER=simulated`. Después envía:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"message":"Responde brevemente: ¿qué es un API?", "provider":"bedrock"}'
```

La llamada solo tendrá coste si el proveedor Bedrock llega a invocarse.

## Límites de uso

Las rutas de chat y tarot aplican por defecto estos límites diarios por usuario:

- 5 lecturas de tarot.
- 20 consultas al asistente.

El backend identifica al usuario mediante el `sub` validado del access token de
Cognito. Para pruebas controladas se pueden configurar `SANDBOX_USER_IDS` o
`SANDBOX_USER_EMAILS`; el `sub` es preferible porque algunos access tokens no
incluyen el email.

En DynamoDB, crea la tabla de contadores una sola vez:

```bash
aws dynamodb create-table \
  --table-name ai-assistant-usage-dev \
  --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=period_key,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH AttributeName=period_key,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

El rol que usa la tarea ECS debe tener `dynamodb:UpdateItem` sobre el ARN
`arn:aws:dynamodb:eu-west-1:740862652747:table/ai-assistant-usage-dev`.
