# Lambda Processing AI

Lambda especializada no processamento de IA para o sistema de detecção e análise de maturação de frutas. Responsável pela execução dos modelos de visão computacional e análise de maturação em instâncias ECR dedicadas.

## Funcionalidades

- Processamento de mensagens SQS com requisições de análise
- Integração com serviço de IA executando em instâncias ECR
- Detecção de objetos e análise de maturação combinadas
- Salvamento de resultados no DynamoDB
- Upload de imagens processadas para S3
- Sistema de retry automático para falhas temporárias
- Monitoramento de status em tempo real
- Tratamento robusto de erros com categorização

## Estrutura

```
lambda-processing-ai/
├── src/
│   ├── app/
│   │   ├── config.py           # Configurações da aplicação
│   │   └── lambda_handler.py   # Handler principal do Lambda
│   └── processor/
│       ├── processing_service.py      # Orquestrador principal
│       ├── repository/
│       │   ├── dynamo_repository.py   # Acesso ao DynamoDB
│       │   └── ia_repository.py       # Integração com IA
│       ├── usecase/
│       │   └── combined_processing_usecase.py # Caso de uso principal
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

**Ambiente e Logs**
- `ENVIRONMENT`: Ambiente (hml/prod)
- `LOG_LEVEL`: Nível de logging (INFO)
- `AWS_REGION`: Região AWS (us-east-1)

**Integração SQS**
- `SQS_QUEUE_URL`: URL da fila SQS

**Armazenamento**
- `DYNAMODB_TABLE_NAME`: Tabela DynamoDB de resultados
- `S3_IMAGES_BUCKET`: Bucket de imagens originais
- `S3_RESULTS_BUCKET`: Bucket de resultados processados

**Serviço de IA**
- `EC2_IA_ENDPOINT`: Endpoint do serviço de IA (ex: http://10.0.1.100:8001)
- `REQUEST_TIMEOUT`: Timeout para requisições à IA (300s)

**Parâmetros de IA**
- `MIN_DETECTION_CONFIDENCE`: Confiança mínima para detecção (0.6)
- `MIN_MATURATION_CONFIDENCE`: Confiança mínima para maturação (0.7)

**Sistema de Retry**
- `MAX_RETRY_ATTEMPTS`: Tentativas máximas (3)
- `RETRY_DELAY_SECONDS`: Delay entre tentativas (5s)

### Mensagem SQS Esperada

```json
{
  "request_id": "req-combined-abc123",
  "image_url": "https://bucket.s3.amazonaws.com/user123/2025/01/01/image.jpg",
  "user_id": "user123",
  "result_upload_url": "https://bucket.s3.amazonaws.com/results/user123/result.jpg",
  "metadata": {
    "image_id": "img-456",
    "location": "dock-1",
    "processing_type": "combined",
    "timestamp": "2025-01-01T12:00:00Z"
  },
  "maturation_threshold": 0.6
}
```

## Fluxo de Processamento

### 1. Recepção da Mensagem SQS
- Validação dos campos obrigatórios
- Extração dos parâmetros de processamento
- Criação do contexto de execução

### 2. Preparação dos Dados
- Download da imagem do S3 (se necessário)
- Validação do formato e tamanho
- Preparação dos metadados

### 3. Processamento de IA
- Chamada para o serviço EC2 com análise combinada
- Detecção de objetos (frutas)
- Análise de maturação por objeto detectado
- Geração de imagem com anotações

### 4. Processamento dos Resultados
- Upload da imagem processada para S3
- Estruturação dos dados de detecção
- Cálculo de estatísticas agregadas
- Validação da qualidade dos resultados

### 5. Persistência
- Salvamento do resultado completo no DynamoDB
- Atualização do status de processamento
- Registro de metadados de performance
- Notificação de conclusão (opcional)

## Modelos de Dados

### Resultado de Detecção
```json
{
  "status": "success",
  "request_id": "req-combined-abc123",
  "detection": {
    "results": [
      {
        "class_name": "apple",
        "confidence": 0.95,
        "bounding_box": [100, 150, 200, 250],
        "maturation_level": {
          "score": 0.75,
          "category": "ripe",
          "confidence": 0.88
        }
      }
    ],
    "summary": {
      "total_objects": 5,
      "objects_with_maturation": 5,
      "detection_time_ms": 1200,
      "maturation_time_ms": 800,
      "average_maturation_score": 0.72,
      "model_versions": {
        "detection_model": "yolov8-fruit-v2.1",
        "maturation_model": "resnet50-maturation-v1.3"
      }
    }
  },
  "image_result_url": "https://bucket.s3.amazonaws.com/results/processed.jpg",
  "processing_time_ms": 2500,
  "processing_metadata": {
    "image_size": [1920, 1080],
    "processing_config": {
      "detection_threshold": 0.6,
      "maturation_threshold": 0.7
    }
  }
}
```

### Estrutura no DynamoDB
```json
{
  "pk": "RESULT#req-combined-abc123",
  "sk": "COMBINED",
  "entity_type": "COMBINED_RESULT",
  "request_id": "req-combined-abc123",
  "user_id": "user123",
  "image_id": "img-456",
  "status": "success",
  "createdAt": "2025-01-01T12:00:00Z",
  "updatedAt": "2025-01-01T12:02:30Z",
  "processing_time_ms": 2500,
  "detection_result": {...},
  "processing_metadata": {...},
  "ttl": 1672531200
}
```

## Sistema de Retry

### Categorização de Erros
- **RETRYABLE**: Erros de rede, timeouts, indisponibilidade temporária
- **NON_RETRYABLE**: Erros de validação, dados inválidos, problemas permanentes

### Estratégia de Retry
- **Exponential Backoff**: Delay crescente entre tentativas
- **Máximo 3 tentativas** por mensagem
- **Dead Letter Queue** para mensagens que falharam definitivamente

### Códigos de Erro
- `PROCESSING_ERROR`: Erro geral de processamento
- `NETWORK_ERROR`: Problemas de conectividade
- `VALIDATION_ERROR`: Dados de entrada inválidos
- `IA_SERVICE_ERROR`: Falha no serviço de IA
- `STORAGE_ERROR`: Problemas com S3/DynamoDB
- `TIMEOUT_ERROR`: Timeout de processamento

## Performance e Otimização

### Configuração de Lambda
- **Memória**: 2048MB para processamento de imagens
- **Timeout**: 300 segundos para análises complexas
- **Concorrência**: Até 10 execuções simultâneas
- **Provisioned Concurrency**: Para reduzir cold start

### Otimizações Implementadas
- Conexões reutilizáveis para AWS services
- Pool de conexões HTTP para EC2
- Processamento assíncrono interno
- Cache de configurações
- Validação early-exit para dados inválidos

### Monitoramento de Performance
- Tempo total de processamento
- Tempo de download/upload
- Tempo de execução da IA
- Throughput de mensagens processadas

## Deploy

### Desenvolvimento Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis
cp .env.template .env
# Editar .env com valores locais

```

### Deploy com SAM
```bash
# Build da aplicação
sam build

# Deploy guiado
sam deploy --guided

# Deploy direto
sam deploy --parameter-overrides \
  Environment=prod \
  SQSQueueURL=https://sqs.us-east-1.amazonaws.com/123456789012/queue \
  DynamoDBTableName=fruit-detection-prod-results
```

### Deploy Produção
```bash
# Criar pacote de deployment
zip -r lambda-processing-ai.zip src/ requirements.txt

# Atualizar função Lambda
aws lambda update-function-code \
  --function-name fruit-detection-processing-ai-prod \
  --zip-file fileb://lambda-processing-ai.zip

# Atualizar configuração
aws lambda update-function-configuration \
  --function-name fruit-detection-processing-ai-prod \
  --environment Variables='{
    "ENVIRONMENT":"prod",
    "EC2_IA_ENDPOINT":"http://10.0.1.100:8001",
    "DYNAMODB_TABLE_NAME":"fruit-detection-prod-results"
  }'
```

### Deploy com Docker
```bash
# Build da imagem
docker build -t fruit-detection-processing-ai .

# Tag para ECR
docker tag fruit-detection-processing-ai:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/fruit-detection-processing-ai:latest

# Push para ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/fruit-detection-processing-ai:latest

# Atualizar função Lambda
aws lambda update-function-code \
  --function-name fruit-detection-processing-ai-prod \
  --image-uri 123456789012.dkr.ecr.us-east-1.amazonaws.com/fruit-detection-processing-ai:latest
```

## Monitoramento

### CloudWatch Logs
- **Log Group**: `/aws/lambda/fruit-detection-processing-ai-{env}`
- **Retenção**: 7 dias (configurável)
- **Structured Logging**: JSON format para parsing

### Métricas Principais
- **Processing Duration**: Tempo total de processamento
- **IA Service Latency**: Tempo de resposta do EC2
- **Error Rate**: Taxa de erro por tipo
- **Retry Rate**: Frequência de reprocessamento
- **Throughput**: Mensagens processadas por minuto

### Alarmes Configurados
- **High Error Rate**: > 3 erros em 5 minutos
- **High Latency**: > 240s de processamento
- **Throttling**: Limitação de execução detectada
- **Dead Letter Queue**: Mensagens não processáveis

### Dashboards
- Tempo de processamento por etapa
- Taxa de sucesso vs falha
- Distribuição de tipos de erro
- Performance do serviço de IA
- Utilização de recursos AWS

## Tratamento de Erros

### Estratégia por Tipo de Erro

**Erros de Rede/Conectividade**
- Retry automático com backoff exponencial
- Timeout progressivo
- Circuit breaker para serviços indisponíveis

**Erros de Dados**
- Validação rigorosa na entrada
- Sanitização de dados corrompidos
- Logging detalhado para debugging

**Erros de IA**
- Fallback para modelos alternativos
- Degradação graceful da qualidade
- Notificação para reprocessamento manual

**Erros de Armazenamento**
- Retry com jitter para evitar thundering herd
- Verificação de integridade de dados
- Recuperação automática de dados parciais

### Logging e Debugging
```python
# Exemplo de log estruturado
{
  "timestamp": "2025-01-01T12:00:00Z",
  "level": "ERROR",
  "request_id": "req-abc123",
  "error_code": "IA_SERVICE_ERROR",
  "error_message": "Connection timeout to EC2 service",
  "retry_attempt": 2,
  "processing_stage": "ia_processing",
  "duration_ms": 30000,
  "metadata": {
    "image_size": "1920x1080",
    "user_id": "user123"
  }
}
```

## Segurança

### Acesso a Recursos
- **IAM Roles**: Permissões mínimas necessárias
- **VPC Configuration**: Acesso controlado ao EC2
- **Encryption**: Dados em trânsito e repouso
- **Secrets Manager**: Credenciais sensíveis

### Validação de Dados
- Sanitização de URLs de entrada
- Validação de formatos de imagem
- Verificação de tamanhos de arquivo
- Prevenção de ataques de injeção

### Auditoria
- Log de todas as operações críticas
- Rastreamento de alterações de dados
- Correlação de requests por usuário
- Detecção de padrões anômalos

## Dependências

### Principais Bibliotecas
- `boto3==1.38.27`: SDK AWS síncrono
- `aioboto3==15.0.0`: SDK AWS assíncrono
- `aiohttp==3.11.18`: Cliente HTTP assíncrono
- `pydantic==2.9.0`: Validação e serialização
- `python-multipart==0.0.20`: Parsing de dados multipart

### Integração com Serviços
- **SQS**: Fila de mensagens de entrada
- **DynamoDB**: Armazenamento de resultados
- **S3**: Download de imagens e upload de resultados
- **EC2**: Serviço de IA para processamento
- **CloudWatch**: Logs e métricas
- **X-Ray**: Tracing distribuído

### Biblioteca Compartilhada do TCC
- `fruit-detection-shared`: Entidades, modelos e clientes AWS comuns

## Desenvolvimento

### Arquitetura de Código
- **Clean Architecture**: Separação clara de responsabilidades
- **Repository Pattern**: Abstração de acesso aos dados
- **UseCase Pattern**: Encapsulamento da lógica de negócio
- **Dependency Injection**: Facilita testes e manutenção

### Estrutura de Pastas
```
src/processor/
├── processing_service.py      # Orquestrador principal
├── repository/               # Camada de dados
│   ├── dynamo_repository.py  # Operações DynamoDB
│   └── ia_repository.py      # Integração com IA
├── usecase/                  # Casos de uso
│   └── combined_processing_usecase.py
└── utils/                    # Utilitários
    ├── error_handler.py      # Tratamento de erros
    └── retry_handler.py      # Sistema de retry
```

### Padrões Implementados
- **Single Responsibility**: Cada classe tem uma responsabilidade
- **Open/Closed**: Extensível sem modificação
- **Dependency Inversion**: Depende de abstrações
- **Error Handling**: Tratamento consistente de erros

### Testes


### Debugging Local

**Configuração para Desenvolvimento**
```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Configurar ambiente local
export ENVIRONMENT=hom
export LOG_LEVEL=DEBUG
export EC2_IA_ENDPOINT=http://localhost:8001

# Executar processamento local
python -m src.processor.processing_service
```

**Mock do Serviço de IA**
```python
# Para testes locais sem EC2
class MockIARepository:
    async def process_combined(self, image, result_upload_url, threshold):
        return CombinedResult(
            status="success",
            detection=mock_detection_results,
            processing_time_ms=1500
        )
```