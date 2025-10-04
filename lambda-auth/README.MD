# Auth Lambda

Lambda responsável por autenticação e geração de tokens JWT para o sistema de detecção de frutas.

## Endpoints

| Método | Rota   | Descrição                          |
|--------|--------|------------------------------------|
| POST   | /login | Autentica usuário e retorna JWT    |
| GET    | /health| Verifica status da aplicação       |

## Variáveis de Ambiente

| Nome                       | Descrição                               | Default |
|----------------------------|-----------------------------------------|---------|
| ENVIRONMENT                | Ambiente (dev/hom/prod)                 | dev     |
| LOG_LEVEL                  | Nível de log                            | INFO    |
| AWS_REGION                 | Região AWS                              | us-east-1 |
| JWT_SECRET_KEY             | Chave secreta para assinar o JWT        | change   |
| ACCESS_TOKEN_EXPIRE_MINUTES| Tempo de expiração do token (minutos)   | 30      |

## Como rodar localmente

```bash
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8000
```
