# Lambda Processing AI

Lambda especializada no processamento de IA para o sistema de detecção e análise de maturação de frutas.

## Funcionalidades

- Processamento de mensagens SQS com requisições de análise
- Integração com serviço de IA no EC2
- Salvamento de resultados no DynamoDB
- Sistema de retry automático
- Monitoramento de status em tempo real
- Tratamento robusto de erros

## Estrutura

```
lambda-processing-ai/
├── src/
│   ├── app/
│   │   ├── config.py           # Configurações da aplicação
│   │   └── lambda_handler.py   # Handler principal do Lambda
│   └── processor/
│       ├── processing_service.py      # Serviço principal
│       ├── repository/
│       │   ├── dynamo_repository.py   # Acesso ao DynamoDB
│       │   └── ia_repository.py       # Integração com IA
│       ├── usecase/
│       │   └── combined_processing_usecase.py
│       └── utils/
│           ├── error_handler.py       # Tratamento de erros
│           └── retry_handler.py       # Sistema de retry
├── requirements.txt
├── template.yaml              # CloudFormation/SAM
├── Dockerfile
└── .env.template
```

## Configuração

### Variáveis de Ambiente

- `ENVIRONMENT`: Ambiente (hml/prod)
- `SQS_QUEUE_URL`: URL da fila SQS
- `DYNAMODB_TABLE_NAME`: Nome da tabela DynamoDB
- `S3_IMAGES_BUCKET`: Bucket de imagens
- `S3_RESULTS_BUCKET`: Bucket de resultados
- `EC2_IA_ENDPOINT`: Endpoint do serviço de IA
- `REQUEST_TIMEOUT`: Timeout para requisições (300s)
- `MIN_DETECTION_CONFIDENCE`: Confiança mínima detecção (0.6)
- `MIN_MATURATION_CONFIDENCE`: Confiança mínima maturação (0.7)

### Mensagem SQS Esperada

```json
{
  "request_id": "req-combined-abc123",
  "image_url": "https://bucket.s3.amazonaws.com/image.jpg",
  "user_id": "user123",
  "result_upload_url": "url pre assinada pro result bucket",
  "metadata": {
    "image_id": "img-123",
    "location": "dock-1",
    "processing_type": "combined"
  },
  "maturation_threshold": 0.6
}
```

## Deploy

### Desenvolvimento
```bash
sam build
sam deploy --guided
```

### Produção
```bash
aws lambda update-function-code \
  --function-name fruit-detection-processing-ai-prod \
  --zip-file fileb://lambda-processing-ai.zip
```

## Monitoramento

- CloudWatch Logs: `/aws/lambda/fruit-detection-processing-ai-{env}`
- Métricas: Errors, Throttles, Duration
- Alarmes: Configurados via CloudFormation

## Dependências

- `boto3`: AWS SDK
- `aioboto3`: AWS SDK assíncrono
- `aiohttp`: Cliente HTTP assíncrono
- `pydantic`: Validação de dados
- `fruit-detection-shared`: Biblioteca compartilhada