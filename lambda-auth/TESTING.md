# Guia de Testes - Auth Lambda

Este guia mostra como testar os endpoints da API de autenticação.

## Configuração Inicial

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Configure as variáveis de ambiente (opcional):
```bash
export DYNAMODB_TABLE_NAME=fruit-detection-dev-users
export JWT_SECRET_KEY=my-super-secret-key-for-testing
export ACCESS_TOKEN_EXPIRE_MINUTES=30
```

3. Popule o banco com usuários de teste:
```bash
python scripts/seed_users.py
```

4. Inicie a aplicação:
```bash
uvicorn src.app.main:app --reload --port 8000
```

5. Acesse a documentação interativa:
```
http://localhost:8000/docs
```

## Exemplos de Requisições

### 1. Criar Usuário

```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao",
    "password": "senha123",
    "name": "João Silva",
    "email": "joao@example.com",
    "user_type": "user"
  }'
```

**Resposta (201 Created)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "joao",
  "name": "João Silva",
  "email": "joao@example.com",
  "user_type": "user"
}
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao",
    "password": "senha123"
  }'
```

**Resposta (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2FvIiwidXNlcl9pZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsInVzZXJfdHlwZSI6InVzZXIiLCJuYW1lIjoiSm_Do28gU2lsdmEiLCJleHAiOjE3MDk4MjU4MDAsImlhdCI6MTcwOTgyNDAwMH0.abc123...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_type": "user"
}
```

### 3. Verificar Token

```bash
TOKEN="seu_token_aqui"

curl -X GET "http://localhost:8000/auth/verify" \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta (200 OK)**:
```json
{
  "valid": true,
  "username": "joao",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_type": "user",
  "name": "João Silva",
  "expires_at": 1709825800
}
```

### 4. Buscar Usuário por ID

```bash
USER_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X GET "http://localhost:8000/users/$USER_ID"
```

**Resposta (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "joao",
  "name": "João Silva",
  "email": "joao@example.com",
  "user_type": "user"
}
```

### 5. Atualizar Usuário

```bash
USER_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X PUT "http://localhost:8000/users/$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João da Silva Santos",
    "email": "joao.santos@example.com"
  }'
```

**Resposta (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "joao",
  "name": "João da Silva Santos",
  "email": "joao.santos@example.com",
  "user_type": "user"
}
```

### 6. Deletar Usuário

```bash
USER_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X DELETE "http://localhost:8000/users/$USER_ID"
```

**Resposta (204 No Content)**: Sem corpo de resposta

### 7. Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

**Resposta (200 OK)**:
```json
{
  "status": "ok",
  "service": "auth-lambda",
  "version": "1.0.0",
  "timestamp": "2024-03-07T14:30:00.000Z"
}
```

## Códigos de Status HTTP

| Código | Descrição                           |
|--------|-------------------------------------|
| 200    | Sucesso                             |
| 201    | Recurso criado com sucesso          |
| 204    | Sucesso sem conteúdo                |
| 400    | Requisição inválida                 |
| 401    | Não autenticado                     |
| 404    | Recurso não encontrado              |
| 500    | Erro interno do servidor            |

## Testando com Postman

1. Importe a coleção de requisições (se disponível)
2. Configure a variável de ambiente `base_url` para `http://localhost:8000`
3. Execute as requisições na ordem sugerida

## Testando com Swagger UI

Acesse `http://localhost:8000/docs` para uma interface interativa onde você pode:
- Ver todos os endpoints disponíveis
- Testar requisições diretamente no navegador
- Ver exemplos de requests e responses
- Validar schemas automaticamente

## Credenciais de Teste (após executar seed)

| Username | Password  | Tipo   |
|----------|-----------|--------|
| admin    | admin123  | admin  |
| user1    | user123   | user   |
| user2    | user456   | user   |

## Dicas

- Use o token JWT retornado pelo login em requisições que exigem autenticação
- Tokens expiram após 30 minutos por padrão
- Em caso de erro 401, faça login novamente para obter um novo token
- Use ferramentas como [jwt.io](https://jwt.io) para inspecionar tokens JWT
