# Lambda Results Query

Lambda especializada na consulta e recuperação de resultados do sistema de detecção e análise de maturação de frutas. Otimizada para operações de leitura com alta performance e filtros avançados.

## Funcionalidades

- Consulta de resultados por request_id, image_id e user_id
- Listagem paginada de todos os resultados
- Filtros avançados por status, data e usuário
- Geração de relatórios e estatísticas
- Sumários de atividade por usuário
- Análise temporal de resultados
- Cache otimizado para consultas frequentes

## Estrutura

```
lambda-results-query/
├── src/
│   ├── app/
│   │   ├── config.py           # Configurações da aplicação
│   │   ├── lambda_handler.py   # Handler principal do Lambda
│   │   └── main.py            # Aplicação FastAPI
│   ├── routes/
│   │   ├── health.py          # Rotas de monitoramento
│   │   └── results.py         # Rotas de consulta de resultados
│   ├── services/
│   │   └── results_service.py # Lógica de negócio para consultas
│   ├── repository/
│   │   └── dynamo_repository.py # Acesso aos dados no DynamoDB
│   └── utils/
│       └── validator.py       # Validações específicas
├── requirements.txt
├── template.yaml              # CloudFormation/SAM
├── Dockerfile
└── .env.template
```

## Configuração

### Variáveis de Ambiente

- `ENVIRONMENT`: Ambiente (hml/prod)
- `DYNAMODB_TABLE_NAME`: Nome da tabela DynamoDB de resultados
- `S3_RESULTS_BUCKET`: Bucket de resultados processados
- `MAX_QUERY_LIMIT`: Limite máximo de consulta (200)
- `DEFAULT_PAGE_SIZE`: Tamanho padrão da página (20)
- `LOG_LEVEL`: Nível de log (INFO)
- `AWS_REGION`: Região AWS (us-east-1)

### Endpoints de Consulta

#### Consultas Específicas
- `GET /results/request/{request_id}` - Resultado por request_id
- `GET /results/image/{image_id}` - Resultados por image_id
- `GET /results/user/{user_id}` - Resultados por user_id

#### Consultas Gerais
- `GET /results/all` - Todos os resultados (paginado)
  - Parâmetros: `limit`, `page_token`, `status_filter`, `user_id`, `exclude_errors`

#### Relatórios e Estatísticas
- `GET /results/summary` - Resumo geral dos resultados
  - Parâmetros: `days` (padrão: 7 dias)
- `GET /results/stats/user/{user_id}` - Estatísticas por usuário
  - Parâmetros: `days` (padrão: 30 dias)

#### Monitoramento
- `GET /health` - Status básico da aplicação
- `GET /health/detailed` - Status detalhado com dependências
- `GET /health/services` - Status individual dos serviços
- `GET /health/ready` - Verificação de prontidão
- `GET /health/live` - Verificação de vida

## Modelos de Resposta

### Resultado Individual
```json
{
  "request_id": "req-abc123",
  "image_id": "img-456",
  "user_id": "user123",
  "status": "success",
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:02:30Z",
  "processing_time_ms": 2500,
  "image_url": "https://bucket.s3.amazonaws.com/image.jpg",
  "image_result_url": "https://bucket.s3.amazonaws.com/result.jpg",
  "detection_results": {
    "total_objects": 5,
    "objects_with_maturation": 3,
    "average_maturation_score": 0.75,
    "results": [...]
  },
  "processing_metadata": {
    "model_versions": {...},
    "processing_config": {...}
  }
}
```

### Consulta Paginada
```json
{
  "items": [...],
  "total_count": 150,
  "has_more": true,
  "next_page_token": "eyJsYXN0X2V2YWx1YXRlZF9rZXkiOi4uLn0=",
  "current_page_size": 20,
  "filters_applied": {
    "status_filter": "success",
    "exclude_errors": true
  }
}
```

### Resumo de Resultados
```json
{
  "period_days": 7,
  "total_results": 1250,
  "successful_results": 1180,
  "failed_results": 70,
  "success_rate": 94.4,
  "average_processing_time_ms": 2350.5,
  "results_by_status": {
    "success": 1180,
    "error": 70
  },
  "top_users": [
    {"user_id": "user123", "count": 45},
    {"user_id": "user456", "count": 32}
  ],
  "generated_at": "2025-01-01T15:30:00Z"
}
```

### Estatísticas do Usuário
```json
{
  "user_id": "user123",
  "period_days": 30,
  "total_results": 85,
  "successful_results": 78,
  "failed_results": 7,
  "success_rate": 91.8,
  "average_processing_time_ms": 2280.3,
  "last_activity": "2025-01-01T14:25:00Z",
  "daily_activity": [
    {
      "date": "2025-01-01",
      "total": 5,
      "successful": 5,
      "failed": 0
    }
  ],
  "generated_at": "2025-01-01T15:30:00Z"
}
```

## Otimizações de Performance

### Índices DynamoDB
- **RequestIdIndex**: Consulta por request_id
- **UserIdIndex**: Consulta por user_id
- **EntityTypeIndex**: Consulta por tipo de entidade
- **StatusIndex**: Filtros por status

### Estratégias de Consulta
- **Query vs Scan**: Preferência por Query quando possível
- **Paginação eficiente**: Uso de tokens de página codificados
- **Filtros no banco**: Aplicação de filtros no DynamoDB
- **Limite de resultados**: Controle de memória e performance

### Cache e Otimização
- Formatação otimizada de resultados
- Reutilização de conexões AWS
- Processamento lazy de dados grandes
- Compressão de tokens de paginação

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
  --function-name fruit-detection-results-query-prod \
  --zip-file fileb://lambda-results-query.zip
```

## Monitoramento

### CloudWatch Logs
- `/aws/lambda/fruit-detection-{env}-results-query`

### Métricas Importantes
- **Query Duration**: Tempo de consulta ao DynamoDB
- **Response Size**: Tamanho das respostas
- **Cache Hit Rate**: Taxa de acerto do cache
- **Error Rate**: Taxa de erro das consultas

### Alarmes Configurados
- **Errors > 5** em 5 minutos
- **High Latency > 10s** para consultas
- **DynamoDB Throttling** detectado

## Padrões de Consulta

### Consultas Frequentes
1. **Por Request ID**: Consulta individual mais comum
2. **Por User ID**: Histórico do usuário
3. **Resultados Recentes**: Últimos processamentos
4. **Por Status**: Filtro de sucessos/erros

### Consultas de Relatório
1. **Resumos Diários**: Estatísticas agregadas
2. **Top Usuários**: Usuários mais ativos
3. **Taxa de Sucesso**: Métricas de qualidade
4. **Tendências Temporais**: Análise de padrões

## Validações

### Parâmetros de Entrada
- **user_id**: Formato alfanumérico, max 128 chars
- **request_id**: Formato `req-xxxxxxxxxx`
- **image_id**: String não vazia, max 128 chars
- **Paginação**: Limite entre 1-200 itens
- **Filtros**: Valores válidos para status

### Segurança
- Validação de permissões por usuário
- Rate limiting por IP
- CORS configurado para consultas
- Headers de cache apropriados

## Limitações

### Performance
- **Timeout**: 30 segundos por consulta
- **Memória**: 512MB
- **Resultados**: Máximo 200 por consulta
- **Relatórios**: Máximo 1000 registros analisados

### Funcional
- Consultas apenas de leitura
- Cache invalidado automaticamente
- Filtros limitados aos índices existentes

## Tratamento de Erros

### Códigos de Status
- `200`: Consulta realizada com sucesso
- `400`: Parâmetros inválidos
- `404`: Resultado não encontrado
- `429`: Rate limit excedido
- `500`: Erro interno de consulta

### Estratégias de Recuperação
- Retry automático para erros temporários
- Fallback para consultas alternativas
- Cache de resultados para consultas frequentes
- Logs detalhados para debugging

## Dependências

### Principais
- `fastapi`: Framework web para API
- `mangum`: Adaptador ASGI para Lambda
- `boto3`: SDK AWS para DynamoDB
- `pydantic`: Validação e serialização
- `fruit-detection-shared`: Modelos compartilhados

### Integração
- **DynamoDB**: Armazenamento principal
- **S3**: URLs de resultados
- **CloudWatch**: Logs e métricas

## Desenvolvimento

### Boas Práticas
- Repository pattern para acesso aos dados
- Service layer para lógica de negócio
- Dependency injection para testabilidade
- Validação em múltiplas camadas

### Estrutura de Dados
- Normalização de respostas
- Formatação consistente de datas
- Tipagem forte com Pydantic
- Documentação automática da API

### Testes (FUTURO)
```bash
# Executar testes unitários
pytest tests/unit/

# Testes de integração
pytest tests/integration/

# Com cobertura
pytest --cov=src tests/
```