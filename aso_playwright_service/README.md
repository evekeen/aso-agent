# ASO Playwright Service

A microservice for ASO Mobile keyword analysis using Playwright automation.

## Features

- **Sequential Processing**: Internal queue ensures only one browser session at a time
- **Fresh Browser Sessions**: Creates new Playwright instance for each task
- **BrowserCat Integration**: Uses BrowserCat for reliable browser automation
- **FastAPI**: Modern async HTTP API with automatic documentation
- **Health Checks**: Built-in health monitoring endpoints

## API Endpoints

- `POST /analyze-keywords` - Analyze keywords for difficulty and traffic
- `GET /health` - Health check endpoint
- `GET /status` - Service status and queue information
- `GET /docs` - Interactive API documentation

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env

# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env

# Run the service
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Option 3: Production Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run with gunicorn
gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ASO_EMAIL` | ASO Mobile email | Required |
| `ASO_PASSWORD` | ASO Mobile password | Required |
| `ASO_APP_NAME` | App name to select | "Bedtime Fan" |
| `BROWSER_CAT_API_KEY` | BrowserCat API key | Required |

## Usage

### Analyze Keywords

```bash
curl -X POST "http://localhost:8001/analyze-keywords" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["sleep sounds", "white noise", "meditation"]}'
```

### Health Check

```bash
curl http://localhost:8001/health
```

### API Documentation

Visit `http://localhost:8001/docs` for interactive API documentation.

## Monitoring

The service provides built-in monitoring endpoints:

- **Health Check**: `GET /health` - Service health status
- **Status**: `GET /status` - Queue status and worker information
- **Logs**: Service logs provide detailed execution information

## Deployment

### Docker

```bash
# Build image
docker build -t aso-playwright-service .

# Run container
docker run -d \
  --name aso-service \
  -p 8001:8001 \
  --env-file .env \
  aso-playwright-service
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aso-playwright-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aso-playwright-service
  template:
    metadata:
      labels:
        app: aso-playwright-service
    spec:
      containers:
      - name: aso-playwright-service
        image: aso-playwright-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: ASO_EMAIL
          valueFrom:
            secretKeyRef:
              name: aso-secrets
              key: email
        - name: ASO_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aso-secrets
              key: password
        - name: BROWSER_CAT_API_KEY
          valueFrom:
            secretKeyRef:
              name: aso-secrets
              key: browsercat-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: aso-playwright-service
spec:
  selector:
    app: aso-playwright-service
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP
```

## Important Notes

- **Single Worker**: Service uses single worker to prevent browser conflicts
- **Fresh Sessions**: Each task creates a new browser instance
- **Queue Processing**: Tasks are processed sequentially via internal queue
- **Timeout**: Tasks timeout after 5 minutes
- **Error Handling**: Failed tasks return empty results (matches original behavior)

## Troubleshooting

### Service won't start
- Check environment variables are set correctly
- Verify BrowserCat API key is valid
- Ensure port 8001 is available

### Browser connection fails
- Verify BrowserCat API key
- Check network connectivity
- Review service logs for detailed error messages

### Tasks timeout
- Check ASO Mobile website availability
- Verify credentials are correct
- Monitor service logs for specific errors