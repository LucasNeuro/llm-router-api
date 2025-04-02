# API MCP + LLM Router + RAG Neo4j

API robusta em Python usando FastAPI que implementa o Model Context Protocol (MCP) com roteamento inteligente de LLMs e RAG usando Neo4j.

## 🚀 Funcionalidades

- **Servidor MCP**: Integração padronizada de recursos, ferramentas e prompts
- **Roteador LLM**: Distribuição inteligente entre DeepSeek e Gemini
- **RAG com Neo4j**: Sistema de recuperação contextual usando banco de dados em grafo

## 📋 Pré-requisitos

- Python 3.10+
- Neo4j Database
- Chaves de API para DeepSeek e Google Gemini

## 🔧 Instalação

1. Clone o repositório
```bash
git clone [url-do-repositorio]
cd mpc
```

2. Instale as dependências
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

4. Inicie o servidor
```bash
python -m api.main
```

## 🛠️ Endpoints Principais

- `POST /mcp/tools/call`: Chamada de ferramentas MCP
- `GET /mcp/resources`: Lista recursos disponíveis
- `POST /chat`: Roteamento para DeepSeek ou Gemini
- `POST /graph/query`: Consultas Neo4j para RAG

## 📦 Estrutura do Projeto

```
/api
└── main.py
└── config.py
└── routers/
    ├── mcp_tools.py
    ├── mcp_resources.py
    ├── llm_router.py
    └── graph_query.py
└── mcp/
    ├── tools/
    ├── resources/
    └── prompts/
└── neo4j/
    ├── connector.py
    └── queries.py
```

## 🔐 Segurança

- Autenticação via JWT
- Variáveis sensíveis em arquivo .env
- Logs detalhados de todas as operações

## 📄 Licença

Este projeto está sob a licença MIT - veja o arquivo [LICENSE.md](LICENSE.md) para detalhes 