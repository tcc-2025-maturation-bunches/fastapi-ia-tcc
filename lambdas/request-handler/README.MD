# Lambda Request Handler

Lambda especializada na manipulação de requisições e orquestração inicial do sistema de detecção e análise de maturação de frutas. Atua como ponto de entrada da arquitetura serverless, recebendo requisições via API Gateway e orquestrando o processamento assíncrono.

## Funcionalidades

- Recepção e validação de requisições via API Gateway
- Geração de URLs pré-assinadas para upload de imagens e resultados
- Orquestração de processamento assíncrono via SQS
- Rastreamento inicial de status de processamento
- Monitoramento de saúde da aplicação
- Processamento em lote de múltiplas imagens
- Sistema de validação robusto

## Estrutura

```
lambda-request-handler/
├── src/
│   ├── app/
│   │   ├── config.py           # Configurações da aplicação
│   │   ├── lambda_handler.py   # Handler principal do Lambda
│   │   └── main.py            # Aplicação FastAPI
│   ├── routes/
│   │   ├── combined.py        # Rotas de processamento combinado
│   │   ├── health.py          # Rotas de monitoramento
│   │   └── storage.py         # Rotas de armazenamento
│   ├── services/
│   │   ├── presigned_service.py    # Geração de URLs pré-assinadas
│   │   ├── queue_service.py        # Integração com SQS
│   │   └── status_service.py       # Gerenciamento de status
│   └── utils/
│       └── validators.py      # Validações de entrada
├── requirements.txt
├── template.yaml              # CloudFormation/SAM
├── Dockerfile
└── .env.template
```

## Configuração

### Variáveis de Ambiente

- `ENVIRONMENT`: Ambiente (hml/prod)
- `SQS_QUEUE_URL`: URL da fila SQS para processamento
- `DYNAMODB_TABLE_NAME`: Nome da tabela DynamoDB
- `S3_IMAGES_BUCKET`: Bucket para imagens originais
- `S3_RESULTS_BUCKET`: Bucket para resultados processados
- `PRESIGNED_URL_EXPIRY_MINUTES`: Expiração das URLs (15 min)
- `MAX_UPLOAD_SIZE_MB`: Tamanho máximo de upload (10MB)
- `MIN_DETECTION_CONFIDENCE`: Confiança mínima detecção (0.6)
- `MIN_MATURATION_CONFIDENCE`: Confiança mínima maturação (0.7)

### Endpoints Principais

#### Processamento Combinado
- `POST /combined/process` - Enviar imagem para processamento
- `GET /combined/status/{request_id}` - Consultar status
- `GET /combined/user/{user_id}/requests` - Requisições do usuário
- `POST /combined/batch-process` - Processamento em lote
- `GET /combined/queue/stats` - Estatísticas da fila

#### Armazenamento
- `POST /storage/presigned-url` - URL pré-assinada para imagem
- `POST /storage/presigned-result-url` - URL pré-assinada para resultado
- `POST /storage/batch-presigned-urls` - URLs em lote
- `GET /storage/validate/{key}` - Validar existência de arquivo

#### Monitoramento
- `GET /health` - Status básico da aplicação
- `GET /health/detailed` - Status detalhado com dependências
- `GET /health/ready` - Verificação de prontidão
- `GET /health/live` - Verificação de vida

## Fluxo de Processamento

1. **Recepção da Requisição**
   - Validação dos dados de entrada
   - Geração de `request_id` único

2. **Preparação**
   - Criação de status inicial no DynamoDB
   - Geração de URL pré-assinada para resultado (se necessário)

3. **Enfileiramento**
   - Envio de mensagem para fila SQS
   - Retorno de resposta imediata ao cliente

4. **Monitoramento**
   - Consulta de status via endpoints dedicados
   - Rastreamento de progresso em tempo real

## Modelos de Dados

### Requisição de Processamento
```json
{
  "image_url": "https://bucket.s3.amazonaws.com/image.jpg",
  "metadata": {
    "user_id": "user123",
    "image_id": "img-123",
    "location": "dock-1",
    "processing_type": "combined"
  },
  "maturation_threshold": 0.6,
  "result_upload_url": "url_opcional"
}
```

### Resposta de Processamento
```json
{
  "request_id": "req-abc123",
  "status": "queued",
  "message": "Solicitação enfileirada com sucesso",
  "queue_position": 3,
  "estimated_wait_time_seconds": 90
}
```

### Status de Processamento
```json
{
  "request_id": "req-abc123",
  "status": "processing",
  "progress": 0.7,
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:02:30Z",
  "elapsed_seconds": 150,
  "is_timeout": false
}
```

## Deploy

### Desenvolvimento Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar localmente
python src/app/main.py
```

### Deploy SAM
```bash
# Build e deploy
sam build
sam deploy --guided
```

### Deploy Produção
```bash
# Atualizar código da função
aws lambda update-function-code \
  --function-name fruit-detection-request-handler-prod \
  --zip-file fileb://lambda-request-handler.zip
```

## Monitoramento

### CloudWatch Logs
- `/aws/lambda/fruit-detection-{env}-request-handler`

### Métricas Importantes
- **Errors**: Número de erros da função
- **Throttles**: Limitações de execução
- **Duration**: Tempo de execução
- **Invocations**: Número de invocações

### Alarmes Configurados
- **Errors > 5** em 5 minutos
- **Throttles > 10** em 5 minutos
- **Duration > 25s** (próximo ao timeout de 30s)

## Dependências

### Principais
- `fastapi`: Framework web assíncrono
- `mangum`: Adaptador ASGI para Lambda
- `boto3`: SDK AWS
- `pydantic`: Validação de dados
- `uvicorn`: Servidor ASGI

### Integração
- `fruit-detection-shared`: Biblioteca compartilhada

## Validações

### Entrada
- **user_id**: Alfanumérico, max 128 chars
- **request_id**: Formato `req-xxxxxxxxxx`
- **image_url**: URL válida do S3
- **metadata**: Campos obrigatórios (user_id, image_id, location)

### Segurança
- Validação de tipos de arquivo (JPEG, PNG)
- Limite de tamanho (10MB)
- CORS configurado
- Headers de segurança

## Limitações

- **Timeout**: 30 segundos por requisição
- **Memória**: 1024MB
- **Upload**: Máximo 10MB por arquivo
- **Batch**: Máximo 10 imagens por lote
- **Rate Limit**: 100 requisições/minuto por usuário

## Tratamento de Erros

### Códigos de Status
- `200`: Sucesso
- `202`: Processamento aceito (assíncrono)
- `400`: Dados inválidos
- `404`: Recurso não encontrado
- `500`: Erro interno

### Logs Estruturados
- Request/Response logging
- Métricas de performance
- Rastreamento de erros
- Correlação de requisições

## Desenvolvimento

### Estrutura de Código
- **Separação por responsabilidades**
- **Dependency Injection**
- **Validação em camadas**
- **Tratamento centralizado de erros**

### Testes (Futuro)
```bash
# Executar testes
pytest tests/

# Com cobertura
pytest --cov=src tests/
```

### Linting
```bash
# Formatação
black src/
ruff check src/
mypy src/
```