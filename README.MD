# FastAPI em AWS Lambda: Projeto de IA para Detecção e Maturação de Frutas

Este projeto implementa uma arquitetura de microsserviços baseada em FastAPI e hospedada em AWS Lambda para o processamento de imagens de frutas, utilizando modelos de Inteligência Artificial para detecção de objetos e análise de maturação.

## INFORMAÇÕES SOBRE O TCC
#### Título: Solução de Visão Computacional para controle de validade em mercados.
#### Faculdade: Instituto Mauá de Tecnologia
#### Curso: Ciência da Computação

##### Alunos:
1. Leonardo Guilmo Chin
2. Luigi Guimarães Trevisan
3. Refael Bidetti Baldi Simões Ferreira
4. Rodrigo Diana Siqueira
5. Vitor Moretti Negresiolo

##### Orientadores:
1. Milkes Yone Alvarenga
2. Sandro Martini
3. Gabriel de Souza Lima

## Arquitetura Atual

O sistema evoluiu para uma arquitetura de microsserviços serverless na AWS, visando maior escalabilidade, manutenibilidade e separação de responsabilidades. Os componentes principais são:

1.  **Frontend**: Uma interface em React para interação do usuário e visualização dos resultados.
2.  **API Layer (API Gateway)**: Atua como a porta de entrada para todas as requisições, roteando-as para os Lambdas apropriados.
3.  **Microsserviços (AWS Lambda com FastAPI)**: Cada Lambda representa um serviço especializado com responsabilidades bem definidas.
4.  **Armazenamento (S3 & DynamoDB)**: Amazon S3 é utilizado para o armazenamento de imagens (originais e processadas) e o DynamoDB para persistir metadados, status e resultados das análises.
5.  **Inteligência Artificial (Amazon EC2)**: Os modelos de IA para detecção e maturação são hospedados em instâncias EC2, proporcionando um ambiente com maior poder de processamento.
6.  **Comunicação Assíncrona (Amazon SQS & SNS)**: SQS gerencia as filas de processamento de imagens, garantindo que as requisições sejam processadas de forma assíncrona. SNS é usado para notificações entre serviços, como a notificação de conclusão de processamento para o gerenciamento de dispositivos.

### De-Para: Evolução da Arquitetura

A tabela abaixo compara a arquitetura da primeira entrega com a estrutura atual de microsserviços.

| Primeira Entrega (Monolito)                                                                                                                  | Arquitetura Atual (Microsserviços) | Justificativa da Mudança                                                                                                                                    |
|:---------------------------------------------------------------------------------------------------------------------------------------------| :--- |:------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Backend Único (Lambda)**: Uma única função Lambda continha toda a lógica de negócio, incluindo a geração de URLs, orquestração e consulta. | **Múltiplos Lambdas Especializados**: A lógica foi dividida em cinco microsserviços distintos (`Request Handler`, `Processing AI`, `Results Query`, `Device Management`, `Auth`). | **Separação de Responsabilidades**: Cada serviço tem um propósito claro, facilitando a manutenção e o desenvolvimento paralelo.                             |
| **Código Compartilhado Interno**: Módulos de domínio e infraestrutura faziam parte da mesma base de código do Lambda.                        | **`shared-libs`**: Uma biblioteca Python compartilhada (`fruit-detection-shared`) foi criada e é instalada como uma dependência em cada Lambda. | **Reutilização e Consistência**: Centraliza entidades de domínio, modelos de dados e clientes de infraestrutura, garantindo consistência entre os serviços. |
| **Gerenciamento de Estado Simples**: O estado do processamento era gerenciado de forma básica dentro da tabela principal.                    | **Rastreamento de Status Detalhado**: O `Request Handler` cria um registro de status inicial, que é atualizado pelo `Processing AI`, permitindo o rastreamento do progresso em tempo real. | **Melhor Experiência do Usuário**: Permite que o cliente consulte o andamento de suas solicitações assíncronas.                                             |
| **Sem Gerenciamento de Dispositivos**: Não havia um serviço dedicado para gerenciar dispositivos de captura.                                 | **`lambda-device-management`**: Um serviço completo para registrar, monitorar (via heartbeats) e configurar dispositivos como Raspberry Pi. | **Escalabilidade e IoT**: Suporta a integração com dispositivos de hardware para captura automática de imagens.                                             |
| **Sem Autenticação**: A API era aberta a todos.                                                                                              | **`lambda-auth`**: Um serviço dedicado para autenticação e gerenciamento de usuários, utilizando tokens JWT. | **Segurança**: Controla o acesso à API e permite a associação de requisições a usuários específicos. Controlado via API Gateway                             |

## Estrutura do Projeto

O repositório está organizado em módulos, cada um representando um microsserviço ou recurso compartilhado.

```
fastapi-ia-tcc/
├── lambda-auth/                # Serviço de autenticação e gerenciamento de usuários
├── lambda-device-management/   # Serviço para gerenciar dispositivos de captura (Raspberry Pi)
├── lambda-processing-ai/       # Serviço que consome da fila SQS e processa as imagens com a IA
├── lambda-request-handler/     # Ponto de entrada da API, orquestra o processamento e upload de imagens
├── lambda-results-query/       # Serviço otimizado para consulta de resultados
├── shared-libs/                # Biblioteca compartilhada com código comum
└── ...                         # (outros arquivos de configuração)
```

## Microsserviços

### 1. Request Handler (`lambda-request-handler`)
- **Responsabilidade**: Ponto de entrada principal da API. Valida requisições, gera URLs pré-assinadas para upload no S3, enfileira tarefas de processamento no SQS e gerencia o status inicial das requisições.
- **Tecnologias**: FastAPI, AWS Lambda, S3, SQS, DynamoDB.

### 2. Processing AI (`lambda-processing-ai`)
- **Responsabilidade**: Consome mensagens da fila SQS, orquestra a chamada para o modelo de IA no EC2, atualiza o status do processamento no DynamoDB e notifica outros serviços (via SNS) sobre a conclusão.
- **Tecnologias**: AWS Lambda, SQS, DynamoDB, EC2 (via HTTP client), SNS.

### 3. Results Query (`lambda-results-query`)
- **Responsabilidade**: Fornece endpoints otimizados para consulta de resultados de processamento. Permite a busca por diversos critérios (ID da requisição, ID do usuário, etc.) e a geração de estatísticas e sumários.
- **Tecnologias**: FastAPI, AWS Lambda, DynamoDB (com GSIs).

### 4. Device Management (`lambda-device-management`)
- **Responsabilidade**: Gerencia o ciclo de vida de dispositivos de hardware (ex: Raspberry Pi), incluindo registro, monitoramento de atividade (heartbeat), configuração remota e rastreamento de estatísticas de captura.
- **Tecnologias**: FastAPI, AWS Lambda, DynamoDB, SNS (para receber notificações).

### 5. Auth (`lambda-auth`)
- **Responsabilidade**: Lida com a autenticação de usuários (login) e o gerenciamento de contas (CRUD de usuários). Emite e valida tokens JWT para proteger os endpoints da API.
- **Tecnologias**: FastAPI, AWS Lambda, DynamoDB, JWT.

### 6. Shared Library (`shared-libs`)
- **Responsabilidade**: Contém o código comum a todos os microsserviços, como entidades de domínio (ex: `User`, `Device`), modelos Pydantic, clientes para serviços AWS (`S3Client`, `DynamoClient`) e mappers. É empacotada e instalada como uma dependência.
- **Tecnologias**: Python, Pydantic, Boto3.

## Configuração do DynamoDB - Índices Secundários Globais (GSI)

Para o funcionamento correto das funcionalidades de consulta, é **essencial** criar manualmente os Índices Secundários Globais (GSI) nas tabelas do DynamoDB.

### GSI: `EntityTypeIndex`
- **Necessário em**: Tabela de Resultados e Tabela de Dispositivos.
- **Chave de Partição (PK)**: `entity_type` (String)
- **Chave de Ordenação (SK)**: `created_at` (String)
- **Projeção**: `ALL`

Este índice otimiza consultas como "buscar todos os resultados" ou "buscar todos os dispositivos", ordenando-os cronologicamente.

### Outros Índices Recomendados
- **`UserIdIndex`**: Para buscar resultados por usuário.
- **`RequestIdIndex`**: Para buscar um resultado por seu ID de requisição.
- **`ImageIdIndex`**: Para buscar resultados associados a uma imagem específica.
- **`DeviceLocationIndex`**: Para buscar dispositivos por localização.
- **`DeviceStatusIndex`**: Para buscar dispositivos por status (ativo/inativo).


## Como Executar Localmente

1.  **Clone o repositório**:
    ```bash
    git clone https://github.com/tcc-2025-maturation-bunches/fastapi-ia-tcc
    cd fastapi-ia-tcc
    ```

2.  **Crie e ative um ambiente virtual**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instale as dependências de desenvolvimento**:
    Isso instalará as dependências de todos os serviços e as ferramentas de lint/testes.
    ```bash
    pip install -r requirements-dev.txt
    ```

4.  **Instale a biblioteca compartilhada (`shared-libs`) em modo editável**:
    Isso permite que as alterações na `shared-libs` sejam refletidas imediatamente nos outros serviços.
    ```bash
    make install-shared
    ```

5.  **Configure as variáveis de ambiente**:
    Cada diretório de lambda (`lambda-*`) contém um arquivo `.env.template`. Copie-o para um arquivo `.env` e preencha as variáveis necessárias para o seu ambiente local (ex: URLs de serviços, nomes de tabelas).

6.  **Execute um dos microsserviços**:
    Navegue até o diretório do serviço desejado e inicie o servidor Uvicorn. Por exemplo, para o `request-handler`:
    ```bash
    cd lambda-request-handler/
    uvicorn src.app.main:app --reload --port 8000
    ```
    Acesse a documentação interativa em: `http://localhost:8000/docs`.

## Implantação

O projeto utiliza **GitHub Actions** para CI/CD automatizado. Além disso, cada serviço contém seu próprio template de `template.yaml` para deploy via **AWS SAM**, facilitando a implantação na infraestrutura da AWS.