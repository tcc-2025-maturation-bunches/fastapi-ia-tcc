# Auth Lambda

Lambda responsável por autenticação e gerenciamento de usuários para o sistema de detecção de frutas.

## Funcionalidades

- **Autenticação JWT**: Login com username/password e emissão de tokens JWT
- **Gerenciamento de Usuários**: CRUD completo de usuários
- **Hash de Senhas**: Senhas armazenadas com bcrypt
- **Controle de Acesso**: Suporte a tipos de usuário (admin/user)

## Endpoints

### Autenticação

| Método | Rota         | Descrição                          |
|--------|--------------|-------------------------------------|
| POST   | /auth/login  | Autentica usuário e retorna JWT    |
| GET    | /auth/verify | Verifica validade do token JWT     |

### Usuários

| Método | Rota           | Descrição                          |
|--------|----------------|-------------------------------------|
| POST   | /users/        | Cria novo usuário                  |
| GET    | /users/{id}    | Busca usuário por ID               |
| PUT    | /users/{id}    | Atualiza dados do usuário          |
| DELETE | /users/{id}    | Remove usuário                     |

### Health

| Método | Rota    | Descrição                     |
|--------|---------|-------------------------------|
| GET    | /health | Verifica status da aplicação  |

## Variáveis de Ambiente

| Nome                       | Descrição                               | Default                           |
|----------------------------|-----------------------------------------|-----------------------------------|
| ENVIRONMENT                | Ambiente (dev/hom/prod)                 | dev                               |
| LOG_LEVEL                  | Nível de log                            | INFO                              |
| AWS_REGION                 | Região AWS                              | us-east-1                         |
| DYNAMODB_TABLE_NAME        | Nome da tabela DynamoDB de usuários    | fruit-detection-dev-users         |
| JWT_SECRET_KEY             | Chave secreta para assinar o JWT        | change-this-secret-key-in-production |
| JWT_ALGORITHM              | Algoritmo de assinatura JWT             | HS256                             |
| ACCESS_TOKEN_EXPIRE_MINUTES| Tempo de expiração do token (minutos)   | 30                                |

## Estrutura da Tabela DynamoDB

### Tabela: fruit-detection-{env}-users

**Partition Key**: `username` (String)

**Atributos**:
- `user_id`: UUID do usuário
- `username`: Nome de usuário único
- `password_hash`: Hash bcrypt da senha
- `name`: Nome completo
- `email`: E-mail
- `user_type`: Tipo de usuário (admin/user)
- `created_at`: Data de criação (ISO 8601)
- `updated_at`: Data de última atualização (ISO 8601)

## Como rodar localmente

### Pré-requisitos
- Python 3.13+
- DynamoDB local ou acesso à AWS

### Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar aplicação
uvicorn src.app.main:app --reload --port 8000
```

### Teste

Acesse a documentação interativa em: http://localhost:8000/docs

### Exemplo de Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**Resposta**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_type": "admin"
}
```

### Exemplo de Verificação de Token

```bash
curl -X GET "http://localhost:8000/auth/verify" \
  -H "Authorization: Bearer <seu_token_aqui>"
```

## Deploy

### AWS Lambda

```bash
# Build da imagem Docker
docker build -t lambda-auth .

# Deploy usando SAM
sam build
sam deploy --guided
```

## Segurança

- **IMPORTANTE**: Altere `JWT_SECRET_KEY` em produção
- Senhas são armazenadas com hash bcrypt
- Tokens JWT expiram após 30 minutos (configurável)
