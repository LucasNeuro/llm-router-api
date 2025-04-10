# Sistema de Agentes G4 Telecom

Este documento descreve a implementação do sistema de agentes virtuais inteligentes para a G4 Telecom, utilizando a infraestrutura de LLM Router existente.

## Visão Geral

O sistema de agentes permite criar assistentes virtuais com personalidades específicas, conhecimento personalizado e capacidades definidas. Cada agente é configurado para se comportar e responder de acordo com diretrizes específicas da marca.

### Componentes Principais

1. **Modelo de Agente (Pydantic)**: Define a estrutura de dados do agente, incluindo personalidade, conhecimento, capacidades e configurações.
2. **Serviço de Agente**: Gerencia os agentes e processa mensagens através do LLM Router.
3. **Webhook de WhatsApp**: Recebe e processa mensagens do WhatsApp específicas para um agente.
4. **Sistema de Memória de Conversa**: Mantém o contexto das conversas para respostas mais coerentes.

## Como Funciona

1. Uma mensagem é recebida através do webhook WhatsApp específico do agente.
2. O sistema extrai o texto da mensagem e informações do remetente.
3. O serviço de agente formata um prompt especializado baseado no template do agente, incluindo instruções de personalidade, conhecimento da empresa e diretrizes de resposta.
4. O prompt é enviado ao LLM Router, que escolhe o modelo mais adequado.
5. A resposta é processada, salva na memória de conversa e enviada de volta ao usuário.

## Rotas da API

### Webhook do Agente
- **URL**: `/api/v1/agent/{agent_id}/webhook`
- **Método**: POST
- **Descrição**: Recebe mensagens WhatsApp e processa com o agente específico.
- **Parâmetros de URL**:
  - `agent_id`: ID do agente (ex: "g4-telecom")

### Listar Agentes
- **URL**: `/api/v1/agents`
- **Método**: GET
- **Descrição**: Lista todos os agentes disponíveis no sistema.

## Configuração de um Agente

Os agentes são definidos usando o modelo Pydantic `Agent` com os seguintes componentes:

### 1. Personalidade (AgentPersonality)
Define o tom de voz, traços de personalidade e estilo de linguagem.

```python
personality = AgentPersonality(
    tone="técnico-profissional com toque divertido",
    traits=["amigável", "objetivo", "divertido mas profissional"],
    language_style="acessível e adaptável",
    formality_level="semi-formal com adaptação"
)
```

### 2. Conhecimento (AgentKnowledge)
Define as informações que o agente possui sobre a empresa, produtos e planos.

```python
knowledge = AgentKnowledge(
    company_info={
        "nome": "G4 TELECOM",
        "slogan": "VIVER É ESTÁ CONECTADO"
        # ...outros dados da empresa
    },
    products=[
        {"nome": "Banda Larga", "descrição": "..."}
        # ...outros produtos
    ],
    plans={
        "simples": [
            {"nome": "Plano Prime", "velocidade": "200 Mega", "preço": "R$ 59,99/mês"}
            # ...outros planos
        ]
        # ...outras categorias de planos
    }
)
```

### 3. Capacidades (AgentCapabilities)
Define o que o agente pode fazer.

```python
capabilities = AgentCapabilities(
    can_answer_technical=True,
    can_provide_support=True,
    can_handle_commercial=True,
    can_register_leads=True,
    erp_integration=True
)
```

### 4. Configuração (AgentConfig)
Configurações gerais e gatilhos para transferência a humanos.

```python
config = AgentConfig(
    name="Geovana",
    gender="feminino",
    target_audience=["clientes residenciais", "clientes empresariais"],
    human_handoff_triggers=[
        "falar com atendente",
        "reclamações complexas"
        # ...outros gatilhos
    ]
)
```

### 5. Template de Prompt
Define como o agente deve se comportar nas conversas.

```python
prompt_template = """
Você é {name}, a assistente virtual da G4 TELECOM.

### PERSONALIDADE:
- Seu tom é {tone}
- Você é {traits}
- Use linguagem {language_style}

...resto do template...

### MENSAGEM ATUAL DO CLIENTE:
{message}

### CONTEXTO ANTERIOR (se houver):
{context}
"""
```

## Como Criar um Novo Agente

1. Defina um novo agente no arquivo `api/models/agent.py`:

```python
novo_agente = Agent(
    id="novo-agente-id",
    personality=AgentPersonality(...),
    knowledge=AgentKnowledge(...),
    capabilities=AgentCapabilities(...),
    config=AgentConfig(...),
    prompt_template="..."
)
```

2. Registre o agente no serviço em `api/utils/agent_service.py`:

```python
# No construtor da classe AgentService
self.agents = {
    "g4-telecom": g4_agent,
    "novo-agente-id": novo_agente
}
```

## Testes

Você pode testar os agentes usando o script `api/scripts/test_agent.py`:

```bash
cd api
python scripts/test_agent.py
```

Este script permite testar interações com o agente de forma interativa ou usando mensagens predefinidas.

## Integração com WhatsApp

Para integrar com o WhatsApp, configure o webhook no MegaAPI apontando para:
```
https://seu-dominio.com/api/v1/agent/g4-telecom/webhook
```

## Próximos Passos e Melhorias

1. **Adicionar RAG (Retrieval Augmented Generation)**: Para permitir que os agentes acessem bases de conhecimento maiores e mais específicas.
2. **Detecção de Intenção**: Implementar um sistema para detectar intenções e rotear para agentes especializados.
3. **Dashboard de Administração**: Para gerenciar agentes, visualizar métricas e ajustar configurações.
4. **Treinamento Contínuo**: Implementar feedback loop para melhorar as respostas dos agentes ao longo do tempo.
5. **Integração com ERP**: Conectar com sistemas empresariais para consulta de dados em tempo real.

## Customização e Extensão

O sistema foi projetado para ser facilmente extensível. Novos campos podem ser adicionados aos modelos Pydantic conforme necessário, e novas funcionalidades podem ser implementadas no serviço de agente. 