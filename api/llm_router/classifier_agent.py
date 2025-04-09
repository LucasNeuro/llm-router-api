import google.generativeai as genai
import os
from typing import Dict, Any, List
from api.utils.logger import logger
import re
import logging
import json

logger = logging.getLogger(__name__)

# Configuração do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# URLs das documentações dos modelos
MODEL_DOCS = {
    "gemini": "https://ai.google.dev/docs",
    "deepseek": "https://api-docs.deepseek.com/",
    "mistral": "https://docs.mistral.ai/api/",
    "gpt": "https://platform.openai.com/docs/api-reference"
}

# Características detalhadas dos modelos
MODEL_CAPABILITIES = """
Gemini:
- Melhor em: Conversação natural, respostas rápidas, tarefas gerais
- Pontos fortes:
  * Interações conversacionais fluidas
  * Respostas empáticas e contextuais
  * Explicações simples e diretas
  * Processamento multimodal (imagens, texto)
  * Bom em seguir instruções específicas
- Casos de uso ideais:
  * Chatbot conversacional
  * Explicações básicas
  * Interações que precisam ser naturais
  * Tarefas que envolvem contexto social
  * Respostas rápidas e diretas

DeepSeek:
- Melhor em: Análise técnica, raciocínio complexo, programação
- Pontos fortes:
  * Análise profunda e detalhada
  * Respostas técnicas precisas
  * Raciocínio lógico estruturado
  * Resolução de problemas complexos
  * Explicações científicas detalhadas
- Casos de uso ideais:
  * Análise técnica aprofundada
  * Debugging de código
  * Explicações científicas
  * Problemas que requerem raciocínio estruturado
  * Tarefas que precisam de precisão técnica

Mistral:
- Melhor em: Processamento de linguagem, análise de texto, classificação
- Pontos fortes:
  * Compreensão contextual refinada
  * Respostas concisas e diretas
  * Excelente em tarefas de NLP
  * Boa compreensão de nuances linguísticas
  * Eficiente em resumos e sínteses
- Casos de uso ideais:
  * Análise de sentimento
  * Classificação de texto
  * Resumos e sínteses
  * Tarefas que requerem compreensão linguística
  * Respostas que precisam ser objetivas

GPT:
- Melhor em: Raciocínio avançado, análise complexa, tarefas especializadas
- Pontos fortes:
  * Raciocínio sofisticado e nuançado
  * Análise profunda de conceitos complexos
  * Excelente em tarefas que requerem expertise
  * Capacidade de manter contexto extenso
  * Respostas bem estruturadas e detalhadas
- Casos de uso ideais:
  * Análise de problemas complexos
  * Tarefas que requerem expertise específica
  * Raciocínio lógico avançado
  * Explicações detalhadas e aprofundadas
  * Síntese de informações complexas
"""

# Prompt para análise detalhada
ANALYSIS_PROMPT = """
Você é um especialista em IA com profundo conhecimento dos modelos Gemini, DeepSeek e Mistral.
Sua tarefa é analisar a entrada do usuário e determinar qual modelo seria mais adequado para responder.

Entrada do usuário: "{input_text}"
Tipo de tarefa (se especificado): {task_type}

Analise os seguintes aspectos:
1. Complexidade da pergunta
2. Natureza da tarefa (técnica, conversacional, análise, etc.)
3. Necessidade de conhecimento específico
4. Tipo de resposta esperada
5. Contexto social ou técnico
6. Necessidade de raciocínio estruturado
7. Urgência e precisão necessária

Considere as características de cada modelo:
{capabilities}

Forneça sua análise em formato JSON com:
{
    "model": "nome do modelo recomendado",
    "confidence": "valor entre 0 e 1",
    "reasoning": {
        "complexity_level": "baixa/média/alta",
        "task_nature": "tipo principal da tarefa",
        "key_aspects": ["lista de aspectos importantes identificados"],
        "explanation": "explicação detalhada da escolha"
    }
}
"""

# Palavras-chave para diferentes níveis de complexidade
COMPLEXITY_KEYWORDS = {
    "high": [
        "explique detalhadamente", "analise profundamente", "compare e contraste",
        "avalie criticamente", "investigue", "desenvolva", "elabore",
        "discuta as implicações", "explore as consequências", "analise o impacto",
        "descreva o processo", "explique o funcionamento", "como funciona",
        "por que", "qual a razão", "quais são as causas", "quais são os efeitos"
    ],
    "medium": [
        "explique", "descreva", "resuma", "defina", "liste",
        "quais são", "como fazer", "qual é", "onde está",
        "quando", "quem", "o que", "onde", "como"
    ],
    "low": [
        "sim", "não", "ok", "certo", "errado",
        "verdadeiro", "falso", "bom", "ruim",
        "maior", "menor", "mais", "menos"
    ]
}

# Palavras-chave para tipos específicos de tarefas
TASK_KEYWORDS = {
    "technical": [
        "código", "programação", "algoritmo", "função", "classe",
        "variável", "loop", "recursão", "debug", "erro",
        "sintaxe", "compilação", "execução", "performance",
        "computação", "sistema", "protocolo", "implementação",
        "arquitetura", "tecnologia", "segurança", "criptografia"
    ],
    "analysis": [
        "analise", "compare", "avalie", "investigue",
        "examine", "discuta", "explore", "pesquise",
        "implicações", "impacto", "consequências"
    ],
    "creative": [
        "crie", "desenvolva", "invente", "imagine",
        "sugira", "proponha", "desenhe", "escreva"
    ],
    "factual": [
        "quando", "onde", "quem", "o que",
        "qual", "quantos", "quanto", "como"
    ],
    "complex": [
        "implicações", "consequências", "impacto",
        "teoria", "filosofia", "conceito", "paradigma",
        "metodologia", "framework", "arquitetura",
        "futuro", "próximos anos", "longo prazo",
        "análise profunda", "considerando aspectos",
        "ética", "filosófica", "moral", "consciência",
        "livre arbítrio", "dilemas", "sociedade",
        "emergentes", "frameworks"
    ]
}

# Configurações dos modelos
MODEL_CAPABILITIES_CONFIG = {
    "deepseek": {
        "complexity": ["high", "medium"],
        "tasks": ["technical", "analysis"],
        "strengths": [
            "Análise técnica detalhada",
            "Explicações técnicas complexas",
            "Geração de código",
            "Raciocínio lógico",
            "Comparações técnicas"
        ]
    },
    "mistral": {
        "complexity": ["medium", "low"],
        "tasks": ["creative", "factual"],
        "strengths": [
            "Respostas concisas",
            "Criatividade",
            "Explicações simples",
            "Conversas naturais",
            "Respostas rápidas"
        ]
    },
    "gemini": {
        "complexity": ["medium"],
        "tasks": ["technical", "factual"],
        "strengths": [
            "Versatilidade geral",
            "Respostas equilibradas",
            "Multimodalidade",
            "Tarefas práticas",
            "Explicações básicas"
        ]
    },
    "gpt": {
        "complexity": ["high"],
        "tasks": ["complex", "analysis"],
        "strengths": [
            "Análise profunda",
            "Raciocínio complexo",
            "Expertise específica",
            "Síntese avançada",
            "Projeções futuras"
        ]
    }
}

def analyze_complexity(text: str) -> str:
    """Analisa a complexidade do texto baseado em palavras-chave e padrões"""
    text = text.lower()
    
    # Indicadores de alta complexidade
    high_complexity_indicators = [
        "analise", "implicações", "impacto",
        "discuta", "considere", "avalie",
        "próximos anos", "futuro", "longo prazo",
        "aspectos técnicos", "aspectos práticos"
    ]
    
    # Conta indicadores de alta complexidade
    high_complexity_count = sum(1 for indicator in high_complexity_indicators if indicator in text)
    
    # Analisa comprimento e estrutura da pergunta
    words = text.split()
    has_multiple_aspects = "e" in words or "," in text
    
    if high_complexity_count >= 2 or (high_complexity_count >= 1 and has_multiple_aspects):
        return "high"
    elif high_complexity_count >= 1 or has_multiple_aspects:
        return "medium"
    else:
        return "low"

def identify_task_type(text: str) -> List[str]:
    """Identifica os tipos de tarefa no texto com pesos"""
    text = text.lower()
    task_scores = {}
    
    for task_type, keywords in TASK_KEYWORDS.items():
        score = sum(3 if keyword in text else 0 for keyword in keywords)
        # Bonus para palavras-chave complexas
        if task_type in ["complex", "analysis"]:
            score *= 1.5
        task_scores[task_type] = score
    
    # Retorna os tipos de tarefa com scores não-zero, ordenados por score
    return [task for task, score in sorted(task_scores.items(), key=lambda x: x[1], reverse=True) if score > 0]

def calculate_indicator_weights(text: str, indicators: Dict[str, bool]) -> Dict[str, float]:
    """
    Calcula pesos específicos para cada indicador baseado no texto e contexto
    """
    weights = {
        "technical": 0.0,
        "complex": 0.0,
        "creative": 0.0,
        "practical": 0.0
    }
    
    # Análise de palavras técnicas
    technical_count = sum(1 for keyword in TASK_KEYWORDS["technical"] if keyword.lower() in text.lower())
    weights["technical"] = min(technical_count * 0.2, 1.0)
    
    # Análise de complexidade e filosofia
    complex_count = sum(1 for keyword in TASK_KEYWORDS["complex"] if keyword.lower() in text.lower())
    weights["complex"] = min(complex_count * 0.25, 1.0)  # Aumentado peso para complexidade
    
    # Análise de criatividade
    creative_count = sum(1 for keyword in TASK_KEYWORDS["creative"] if keyword.lower() in text.lower())
    weights["creative"] = min(creative_count * 0.2, 1.0)
    
    # Análise prática
    practical_count = sum(1 for keyword in TASK_KEYWORDS["factual"] if keyword.lower() in text.lower())
    weights["practical"] = min(practical_count * 0.15, 1.0)  # Reduzido peso para prático
    
    return weights

def analyze_indicators(prompt: str) -> Dict[str, Any]:
    """
    Analisa indicadores no prompt para classificação
    """
    # Converte para minúsculas para análise
    text = prompt.lower()
    
    # Análise de complexidade
    complexity = analyze_complexity(text)
    
    # Identifica tipos de tarefa
    task_types = identify_task_type(text)
    
    # Indicadores básicos
    indicators = {
        "complex": complexity == "high",
        "technical": "technical" in task_types,
        "analytical": "analysis" in task_types,
        "simple": complexity == "low"
    }
    
    # Log dos indicadores
    logger.info(f"Indicadores determinados: {json.dumps(indicators, indent=2)}")
    
    return indicators

def calculate_model_scores(indicators: Dict[str, Any]) -> Dict[str, float]:
    """
    Calcula os scores para cada modelo baseado nos indicadores
    """
    scores = {
        "deepseek": 0.0,
        "gemini": 0.0,
        "mistral": 0.0,
        "gpt": 0.0
    }
    
    # Pesos para cada modelo
    weights = {
        "deepseek": {
            "complex": 0.7,
            "technical": 0.6,
            "analytical": 0.5,
            "simple": -0.12  # Aumentada a penalidade para mensagens simples
        },
        "gemini": {
            "complex": 0.3,
            "technical": 0.4,
            "analytical": 0.3,
            "simple": 0.2
        },
        "mistral": {
            "complex": -0.8,  # Aumentada a penalidade para mensagens complexas
            "technical": -0.3,  # Adicionada penalidade para mensagens técnicas
            "analytical": -0.2,  # Adicionada penalidade para mensagens analíticas
            "simple": 0.9  # Aumentada a prioridade para mensagens simples
        },
        "gpt": {
            "complex": 0.5,
            "technical": 0.6,
            "analytical": 0.5,
            "simple": -0.3
        }
    }
    
    # Calcula scores baseado nos indicadores
    for model in scores:
        for indicator, value in indicators.items():
            if value:
                scores[model] += weights[model][indicator]
    
    # Garante um score mínimo positivo para o Mistral em perguntas simples
    if indicators["simple"] and not any([indicators["complex"], indicators["technical"], indicators["analytical"]]):
        scores["mistral"] = max(scores["mistral"], 0.7)
    
    # Normaliza os scores para garantir que somem 1
    total = sum(abs(score) for score in scores.values())
    if total > 0:
        for model in scores:
            scores[model] = scores[model] / total
    
    # Log dos scores calculados
    logger.info(f"Scores dos modelos calculados: {json.dumps(scores, indent=2)}")
    
    return scores

def classify_prompt(prompt: str) -> Dict[str, Any]:
    """Classifica o prompt com nova hierarquia de modelos."""
    # Analisa os indicadores
    indicators = analyze_indicators(prompt)
    
    # Calcula pontuações dos modelos
    model_scores = calculate_model_scores(indicators)
    
    # Thresholds ajustados para nova hierarquia
    thresholds = {
        "complex": 1.5,    # Aumentado para complexidade alta
        "technical": 1.3,  # Ajustado para questões técnicas
        "analytical": 1.2,
        "simple": 0.8
    }
    
    # Determina o nível de complexidade
    complexity_level = "high" if indicators["complex"] else \
                      "medium" if indicators["technical"] > thresholds["technical"] else \
                      "low" if indicators["simple"] > thresholds["simple"] else "medium"
    
    # Escolhe o modelo baseado na complexidade
    if complexity_level == "high" and model_scores["deepseek"] > 0.6:
        recommended_model = "deepseek"
    elif complexity_level == "medium" and model_scores["gemini"] > 0.6:
        recommended_model = "gemini"
    elif complexity_level == "low" and model_scores["mistral"] > 0.6:
        recommended_model = "mistral"
    else:
        # Se nenhum modelo tem confiança suficiente, escolhe o com maior score
        recommended_model = max(model_scores.items(), key=lambda x: x[1])[0]
    
    # Calcula confiança
    scores_sorted = sorted(model_scores.values(), reverse=True)
    confidence = scores_sorted[0] - scores_sorted[1] if len(scores_sorted) > 1 else 1.0
    
    return {
        "model": recommended_model,
        "confidence": confidence,
            "model_scores": model_scores,
        "indicators": {
            "complex": indicators["complex"],
            "technical": indicators["technical"],
            "analytical": indicators["analytical"],
            "simple": indicators["simple"]
        },
        "complexity_level": complexity_level,
        "raw_scores": model_scores,
        "analysis": {
            "complexity_level": complexity_level,
            "task_nature": "unknown",
            "key_aspects": [],
            "explanation": "Analysis based on keywords and task type"
        }
    }