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
  document processor; deployment and queue wiring remain pending.
- Prepared a Lambda container image definition with the backend runtime
  dependencies.
- Created the ECR repository `ai-assistant-document-processor` in
  `eu-west-1`.
- Built, tagged and published the Lambda container image to ECR with digest
  `sha256:1fc03d8eb9253c28eeab2c70f553fb2d786b869b0ce7736888f8fc2506bddd8f`.
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
- The backend and frontend are still running locally during development.
- No public application domain has been configured yet.

## TODO

### Ingestion and document lifecycle

- Create the Lambda function from the image already published in Amazon ECR.
- Deploy the Lambda and configure the S3 event notification.
- Add SQS buffering and a dead-letter queue between S3 and Lambda.
- Migrate document and conversation persistence from SQLite to DynamoDB or
  another managed production database.
- Add a durable queue, exponential backoff and dead-letter handling for
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

- Containerize the backend and frontend.
- Define infrastructure as code.
- Deploy the API, frontend and asynchronous processing workflow.
- Add CI/CD, staging and production environments.
- Add backups, retention policies and disaster-recovery procedures.

## Lambda container deployment to ECR

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
source ../.venv/bin/activate
export AWS_PROFILE=ai-assistant-dev
export AWS_REGION=eu-west-1
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
docker build \
  -f Dockerfile.lambda \
  -t ai-assistant-document-processor:latest \
  .
```

Get the AWS account ID and authenticate Docker with ECR:

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
  --profile ai-assistant-dev \
  --query Account \
  --output text)

aws ecr get-login-password \
  --region eu-west-1 \
  --profile ai-assistant-dev \
  | docker login \
  --username AWS \
  --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com
```

Tag and publish the image:

```bash
docker tag \
  ai-assistant-document-processor:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest

docker push \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest
```

The image has been built and published successfully. The ECR image is only a
container artifact; it is not yet a running application or a public domain.
The next deployment steps are creating the Lambda function, configuring its
IAM execution role, adding the Lambda role to the OpenSearch data-access
policy, and connecting the S3 event notification.

## Current URLs and public domain

The application currently runs locally:

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

There is no public domain yet. The ECR URI below identifies the stored image,
not the application URL:

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
