# CloudVisor AI Router Service

Unified LLM gateway providing a single API endpoint for multiple AI providers (OpenAI, OpenRouter, NVIDIA NIM).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CloudVisor Platform                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │   Web    │   │  Copilot │   │  AIOps   │   │  Other   │   │
│  │   UI     │   │  Service │   │  (Keep)  │   │ Services │   │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   │
│       │              │              │              │           │
│       └──────────────┴──────────────┴──────────────┘           │
│                      │                                           │
│              ┌───────▼────────┐                                │
│              │  API Gateway   │                                │
│              │  (/v1/ai/*)    │                                │
│              └───────┬────────┘                                │
│                      │                                           │
│       ┌──────────────┴──────────────┐                           │
│       │                             │                           │
│  ┌────▼────┐  ┌──────────────┐  ┌──▼───┐                      │
│  │OpenAI   │  │  OpenRouter  │  │NVIDIA│    ◄── AI Router    │
│  │(GPT-4o) │  │(Llama/Claude)│  │ NIM  │                      │
│  └─────────┘  └──────────────┘  └──────┘                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Unified API**: Single interface for multiple LLM providers
- **Streaming Support**: Real-time response streaming via SSE
- **Health Monitoring**: Automatic health checks for all providers
- **Provider Fallback**: Automatic failover between providers
- **Rate Limiting**: Built-in rate limiting per tenant
- **Caching**: Redis-backed response caching (optional)

## API Endpoints

### Health Check
```
GET /health
```

### List Providers
```
GET /v1/providers
```

### List Models
```
GET /v1/models?provider={provider_name}
```

### Chat Completion
```
POST /v1/chat/completions
Content-Type: application/json

{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello!"}
  ],
  "provider": "openai",  // optional: openai, openrouter, nvidia
  "model": "gpt-4o-mini", // optional
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

### Streaming Chat Completion
```
POST /v1/chat/completions/stream
Content-Type: application/json

{
  "messages": [...],
  "stream": true
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8015 | Service port |
| `DEFAULT_PROVIDER` | openai | Default LLM provider |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `OPENAI_BASE_URL` | https://api.openai.com/v1 | OpenAI endpoint |
| `OPENROUTER_API_KEY` | - | OpenRouter API key |
| `OPENROUTER_BASE_URL` | https://openrouter.ai/api/v1 | OpenRouter endpoint |
| `NVIDIA_API_KEY` | - | NVIDIA NIM API key |
| `NVIDIA_BASE_URL` | https://integrate.api.nvidia.com/v1 | NVIDIA endpoint |
| `RATE_LIMIT_RPM` | 60 | Requests per minute limit |
| `REDIS_URL` | - | Redis URL for caching |
| `ENABLE_CACHE` | false | Enable response caching |

### Docker Compose

The service is configured in the main `docker-compose.yml`:

```yaml
ai-router:
  build:
    context: .
    dockerfile: services/ai-router/Dockerfile
  container_name: cv-ai-router
  ports:
    - "8015:8015"
  environment:
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
    NVIDIA_API_KEY: ${NVIDIA_API_KEY}
    DEFAULT_PROVIDER: openai
  networks:
    - cloudvisor
```

## Provider Support

### OpenAI
- Models: GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo
- Features: Full streaming, function calling

### OpenRouter
- Models: Llama 3.3, Llama 3.1, Claude 3.5, Gemini Pro, Mistral
- Features: Free tier models, multiple providers

### NVIDIA NIM
- Models: Llama 3.1 (8B/70B/405B), Mistral, Gemma 2
- Features: Optimized inference, enterprise deployment

## Usage Examples

### Python Client
```python
import requests

response = requests.post(
    "http://localhost:8015/v1/chat/completions",
    json={
        "messages": [
            {"role": "user", "content": "Summarize this alert"}
        ],
        "provider": "nvidia",
        "model": "meta/llama-3.1-70b-instruct"
    }
)

result = response.json()
print(result["content"])
```

### cURL
```bash
curl -X POST http://localhost:8015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": "openrouter"
  }'
```

## Integration with Other Services

### From Web Frontend
```typescript
const response = await fetch('/v1/ai/chat/completions', {
  method: 'POST',
  body: JSON.stringify({
    messages: [{ role: 'user', content: prompt }],
    provider: 'nvidia'
  })
});
```

### From Keep AIOps
The Keep service can be configured to use AI Router instead of direct OpenAI:
```env
OPENAI_BASE_URL=http://cv-ai-router:8015/v1
OPENAI_API_KEY=dummy-key
```

## Development

### Local Setup
```bash
cd services/ai-router
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Run locally
uvicorn app.main:app --reload --port 8015
```

### Testing
```bash
# Health check
curl http://localhost:8015/health

# List providers
curl http://localhost:8015/v1/providers
```

### Building
```bash
docker-compose build ai-router
docker-compose up -d ai-router
```

## Future Enhancements

- [ ] Azure OpenAI support
- [ ] AWS Bedrock support
- [ ] Google Vertex AI support
- [ ] Smart routing based on model availability
- [ ] Cost tracking per tenant
- [ ] Request/response logging
- [ ] Fine-tuning model management
