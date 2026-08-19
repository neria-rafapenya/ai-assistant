# ai-assistant

## What we did

This project is an AWS-first AI assistant with a React frontend and a
FastAPI backend. The current implementation includes:

- Created the monorepo structure for `frontend/` and `backend/`.
- Configured local development with Python virtual environment, FastAPI,
  Uvicorn, boto3 and automated tests.
- Configured Git/GitHub workflow and environment variables through `.env`
  and `.env.example`.
- Created an AWS development identity through IAM Identity Center with a
  dedicated developer user and development permissions.
- Created an AWS Budget alert for development cost monitoring.
- Created the S3 document bucket with server-side encryption and the
  `incoming/`, `processed/` and `failed/` prefixes.
- Implemented presigned S3 upload URLs so the frontend uploads documents
  without exposing AWS credentials.
- Implemented PDF processing, text extraction and chunk generation.
- Added local persistence for chat sessions and messages with SQLite.
- Created the DynamoDB development tables for documents and conversations.
- Added DynamoDB repository implementations with SQLite retained as the local
  fallback, selected through `PERSISTENCE_BACKEND`.
- Validated document processing state persistence in DynamoDB from Lambda.
- Validated chat message persistence in DynamoDB with the FastAPI backend.
- Added a GitHub Actions CI workflow that runs backend tests and frontend
  lint/build checks on pushes to `main` and pull requests.
- Added a separate `backend/Dockerfile.backend` for serving the FastAPI API;
  the existing `Dockerfile.lambda` remains dedicated to document jobs.
- Added a vector-store abstraction with local and OpenSearch Serverless
  implementations.
- Created the OpenSearch Serverless vector collection and configured its
  data access policy for the IAM Identity Center role.
- Created the `ai-assistant-documents` index and the
  `ai-assistant-documents-bedrock-512` index.
- Added the Bedrock embedding provider using Titan Text Embeddings V2 with
  configurable vector dimensions.
- Reprocessed documents with real 512-dimensional embeddings and validated
  semantic search in OpenSearch.
- Implemented RAG search and document-processing endpoints.
- Automated document processing after a successful frontend upload, while
  keeping manual reprocessing available for retries.
- Added SQLite persistence for document processing state, attempts, errors,
  processed output and chunk counts.
- Added a maximum retry limit and the document status endpoint.
- Prepared an S3 `ObjectCreated` Lambda handler that reuses the backend
  document processor.
- Prepared a Lambda container image definition with the backend runtime
  dependencies.
- Created the ECR repository `ai-assistant-document-processor` in
  `eu-west-1`.
- Built, tagged and published the Lambda container image to ECR. The image
  was rebuilt for the Lambda-compatible `linux/amd64` platform.
- Created the Lambda function `ai-assistant-document-processor` from the ECR
  image and configured its execution role.
- Configured S3 to publish PDF creation events from `incoming/` to SQS.
- Configured Lambda to consume the SQS queue with a 60-second timeout and
  1024 MB of memory.
- Added an SQS standard queue and dead-letter queue between S3 and Lambda.
- Updated the Lambda handler to process SQS-wrapped S3 notifications.
- Validated the S3 → SQS → Lambda document-processing flow.
- Implemented an Orchestrator that selects the general or RAG route,
  identifies sources and delegates generation to the configured provider.
- Added a simulated provider for safe local development.
- Integrated Amazon Bedrock Converse with Amazon Nova Lite through the
  European inference profile `eu.amazon.nova-lite-v1:0`.
- Added controlled per-request provider selection, keeping `simulated` as
  the default to avoid accidental Bedrock usage.
- Validated the flow with backend tests, frontend build/lint and controlled
  AWS calls.

## Current status

- Real Bedrock text generation is working.
- OpenSearch RAG indexing is working.
- Bedrock embeddings with Titan V2 are working in the development index.
- The simulated embedding provider remains available as a local fallback.
- Automatic S3-to-SQS-to-Lambda PDF processing is working in the development
  account.
- The FastAPI backend is deployed on Amazon ECS Express Mode.
- The React frontend is still running locally during development.
- A custom domain has not been configured yet.

## TODO

### Ingestion and document lifecycle

- Add backups, retention and production data-management policies for the
  DynamoDB tables.
- Add explicit retry/backoff observability and operational alerts for
  processing jobs.
- Add document deletion and re-indexing controls.

### RAG and assistant quality

- Improve chunking for semantic sections instead of fixed-size chunks only.
- Tune multilingual retrieval for Spanish tarot and dream-interpretation
  content.
- Add citations and clearer source references to assistant responses.
- Add evaluation queries and relevance metrics for RAG quality.

### Security and application features

- Add user authentication and authorization to FastAPI and React.
- Isolate documents, conversations and indexes by user or tenant.
- Add request validation, rate limiting and production CORS configuration.
- Implement the tarot-reading and dream-interpretation domain workflows.

### Operations and cost control

- Add structured logging, metrics and error monitoring.
- Add dashboards for S3, OpenSearch and Bedrock usage.
- Create cost simulations by volume of documents, chunks and conversations.
- Review and minimize IAM permissions before production.

### Deployment

- Publish the frontend and configure its public CORS origin.
- Define infrastructure as code.
- Deploy the API, frontend and asynchronous processing workflow.
- Add CD deployment, staging and production environments.
- Add backups, retention policies and disaster-recovery procedures.

## Deployment commands

The commands below assume that Docker Desktop is running, the AWS CLI is
configured with the `ai-assistant-dev` SSO profile, and AWS resources are in
`eu-west-1`.

### Common deployment setup

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant
source .venv/bin/activate
export AWS_PROFILE=ai-assistant-dev
export AWS_REGION=eu-west-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
  --profile ai-assistant-dev \
  --query Account \
  --output text)

aws sso login --profile ai-assistant-dev
aws sts get-caller-identity --profile ai-assistant-dev
```

Authenticate Docker against ECR:

```bash
aws ecr get-login-password \
  --region eu-west-1 \
  --profile ai-assistant-dev \
  | docker login \
  --username AWS \
  --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com
```

### Lambda document processor

The document processor is prepared as a Lambda container image using
`backend/Dockerfile.lambda`. The following procedure builds the image and
publishes it to Amazon ECR in `eu-west-1`.

### Prerequisites

- Docker Desktop must be running.
- AWS CLI must be configured with the `ai-assistant-dev` SSO profile.
- The current directory must be `backend/`.

Check Docker before building:

```bash
docker info
```

If Docker is not running on macOS:

```bash
open -a Docker
```

### Build and publish

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant/backend
```

Create the ECR repository once:

```bash
aws ecr create-repository \
  --repository-name ai-assistant-document-processor \
  --image-scanning-configuration scanOnPush \
  --region eu-west-1 \
  --profile ai-assistant-dev
```

Build the Lambda image:

```bash
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --load \
  -f Dockerfile.lambda \
  -t ai-assistant-document-processor:latest \
  .
```

Tag and publish the image:

```bash
docker tag \
  ai-assistant-document-processor:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest

docker push \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest
```

Update the existing Lambda function to the newly published image:

```bash
aws lambda update-function-code \
  --function-name ai-assistant-document-processor \
  --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest \
  --region eu-west-1 \
  --profile ai-assistant-dev
```

Verify the asynchronous pipeline after uploading a PDF:

```bash
aws s3 cp /ruta/al/documento.pdf \
  s3://ai-assistant-documents-dev-740862652747/incoming/deploy-test.pdf \
  --profile ai-assistant-dev \
  --region eu-west-1

aws logs tail /aws/lambda/ai-assistant-document-processor \
  --since 15m \
  --profile ai-assistant-dev \
  --region eu-west-1

aws s3 ls s3://ai-assistant-documents-dev-740862652747/processed/ \
  --profile ai-assistant-dev \
  --region eu-west-1
```

The Lambda function, S3 notification, SQS trigger and execution role were
created/configured in the AWS Console. The commands above publish and update
the deployable image and verify the resulting flow.

### FastAPI backend image

The HTTP API uses `backend/Dockerfile.backend`, separate from the Lambda
processor image. Create its ECR repository once:

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant/backend

aws ecr create-repository \
  --repository-name ai-assistant-api \
  --image-scanning-configuration scanOnPush \
  --region eu-west-1 \
  --profile ai-assistant-dev
```

Build and publish the API image:

```bash
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --load \
  -f Dockerfile.backend \
  -t ai-assistant-api:latest \
  .

docker tag ai-assistant-api:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-api:latest

docker push \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-api:latest
```

The API image is deployed through Amazon ECS Express Mode. The service uses
the `ecsTaskExecutionRole`, an ECS Express infrastructure role, and a task
role with access to the AWS resources used by the application.

The image has been built and published successfully. The Lambda function,
SQS trigger, S3 notification and DynamoDB document persistence are now
working in the development account. Chat persistence has also been validated
against DynamoDB from the FastAPI backend.
The ECR image is the deployment artifact; it is not a public application
domain.

## Frontend deployment to S3

The React frontend is deployed separately from the Docker-based backend. Each
frontend release is built locally and synchronized to the private S3 bucket
`ai-assistant-frontend-dev-740862652747`. CloudFront will be added later as
the public distribution layer.

### Build and upload a frontend release

Run from `frontend/`:

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant/frontend

# Vite reads VITE_API_BASE_URL from the root .env file.
npm run build

aws s3 sync dist/ \
  s3://ai-assistant-frontend-dev-740862652747/ \
  --profile ai-assistant-dev \
  --region eu-west-1
```

The upload is repeatable: run the same commands after each frontend change.
The current bucket is private, so it is not yet a public website URL. After
CloudFront is configured, invalidate its cache after a release when needed:

```bash
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/*" \
  --profile ai-assistant-dev
```

For the current local-to-remote API test, use this value in `.env` before the
build:

```env
VITE_API_BASE_URL=https://ai-5428103d948647f2ac9aa11b2ba6f07a.ecs.eu-west-1.on.aws
```

## Current URLs and public domain

The application currently runs locally:

- Local backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

The deployed backend API is available at:

```text
https://ai-5428103d948647f2ac9aa11b2ba6f07a.ecs.eu-west-1.on.aws
```

Health check:

```text
https://ai-5428103d948647f2ac9aa11b2ba6f07a.ecs.eu-west-1.on.aws/health
```

There is no custom public domain yet. The ECR URI below identifies the stored
image, not the application URL:

```text
740862652747.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest
```

## Environment variables

Configured in `.env` and documented in `.env.example`:

- `VITE_API_BASE_URL=http://localhost:8000`
- `FRONTEND_ORIGIN=http://localhost:5173`
- `AWS_REGION=eu-west-1`
- `S3_BUCKET_NAME=`
- `AI_PROVIDER=simulated`
- `VECTOR_STORE_BACKEND=opensearch`
- `OPENSEARCH_ENDPOINT=`
- `OPENSEARCH_INDEX=ai-assistant-documents`
- `OPENSEARCH_SERVICE=aoss`
- `BEDROCK_MODEL_ID=eu.amazon.nova-lite-v1:0`
- `BEDROCK_MAX_TOKENS=128`
- `BEDROCK_TEMPERATURE=0.2`
- `EMBEDDING_PROVIDER=simulated`
- `BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0`
- `EMBEDDING_DIMENSIONS=512`
