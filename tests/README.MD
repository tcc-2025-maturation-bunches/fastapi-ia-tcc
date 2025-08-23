# Testes para o Projeto FastAPI em AWS Lambda

Este diretório contém os testes unitários e de integração para o projeto de IA para detecção e maturação de frutas.

## Estrutura dos Testes

Os testes estão organizados da seguinte forma:

- `configtest.py`: Configurações e fixtures compartilhadas por todos os testes
- `.env.test`: Variáveis de ambiente específicas para o ambiente de teste
- `unit/`: Testes unitários
  - `modules/`: Testes para os módulos da aplicação
    - `ia_integration/`: Testes para o módulo de integração com IA
    - `storage/`: Testes para o módulo de armazenamento
  - `shared/`: Testes para os componentes compartilhados
    - `domain/`: Testes para entidades e modelos de domínio
    - `infra/`: Testes para a infraestrutura
- `integration/`: Testes de integração para os endpoints da API

## Execução dos Testes

Para executar os testes localmente, siga estas etapas:

1. Prepare o ambiente:
```bash
# Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências de desenvolvimento
pip install -r requirements-dev.txt
```

2. Execute os testes:
```bash
# Execute todos os testes (com configuração personalizada)
python -m pytest

# Execute com detalhes verbose
python -m pytest -v

# Execute apenas testes unitários
python -m pytest tests/unit/

# Execute apenas testes de integração
python -m pytest tests/integration/

# Execute com relatório de cobertura
python -m pytest --cov=src tests/
```

## Configuração do Ambiente de Teste

O arquivo `.env.test` contém todas as configurações necessárias para o ambiente de teste. Estas configurações são carregadas automaticamente pelo `configtest.py` usando a biblioteca `python-dotenv`.

As variáveis de ambiente definidas incluem:
- `ENVIRONMENT=test`: Define o ambiente como teste
- `DEBUG=True`: Ativa o modo de depuração
- `AWS_REGION=us-east-1`: Define a região AWS
- `DYNAMODB_TABLE_NAME=fruit-detection-test-results`: Nome da tabela DynamoDB para testes
- `S3_IMAGES_BUCKET=fruit-detection-test-images`: Nome do bucket S3 para imagens de teste
- `S3_RESULTS_BUCKET=fruit-detection-test-results`: Nome do bucket S3 para resultados de teste
- `EC2_IA_ENDPOINT=http://localhost:8001`: URL do endpoint de IA para testes
- `REQUEST_TIMEOUT=5`: Timeout reduzido para testes
- `MAX_UPLOAD_SIZE_MB=10`: Tamanho máximo de upload
- `PRESIGNED_URL_EXPIRY_MINUTES=15`: Tempo de expiração das URLs pré-assinadas

## Mocks e Test Doubles

Os testes utilizam mocks para simular os serviços da AWS e outras dependências externas:

- `mock_s3_client`: Mock para o cliente S3
- `mock_dynamo_client`: Mock para o cliente DynamoDB
- `mock_ec2_client`: Mock para o cliente EC2 (serviço de IA)
- `mock_s3_repository`: Mock para o repositório S3
- `mock_dynamo_repository`: Mock para o repositório DynamoDB
- `mock_ia_repository`: Mock para o repositório de IA

Esses mocks permitem testar o código sem necessidade de acesso real aos serviços da AWS.
