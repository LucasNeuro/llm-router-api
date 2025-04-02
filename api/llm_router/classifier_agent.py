import google.generativeai as genai
import os
from typing import Dict, Any, List
from ..utils.logger import logger
import re
import logging
from .gpt import call_gpt

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
        "análise profunda", "considerando aspectos"
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

def classify_prompt(text: str) -> Dict[str, Any]:
    """Classifica o prompt para determinar o melhor modelo"""
    
    # Análise de complexidade
    complexity = analyze_complexity(text.lower())
    text_lower = text.lower()
    
    # Identificação de palavras-chave por tipo de tarefa
    task_keywords = {
        task: sum(1 for keyword in keywords if keyword in text_lower)
        for task, keywords in TASK_KEYWORDS.items()
    }
    
    # Determina o tipo principal de tarefa
    task_type = max(task_keywords.items(), key=lambda x: x[1])[0] if any(task_keywords.values()) else "general"
    
    # Pontuação para cada modelo baseada em suas capacidades
    model_scores = {
        "gpt": 0,
        "deepseek": 0,
        "mistral": 0,
        "gemini": 0
    }
    
    # Análise de complexidade
    if complexity == "high":
        model_scores["gpt"] += 4
        model_scores["deepseek"] += 3
        model_scores["gemini"] += 2
    elif complexity == "medium":
        model_scores["gemini"] += 3
        model_scores["deepseek"] += 2
        model_scores["mistral"] += 2
    else:
        model_scores["mistral"] += 3
        model_scores["gemini"] += 2
        model_scores["gpt"] += 1

    # Análise de palavras-chave específicas para tarefas complexas
    complex_indicators = [
        "analise", "impacto", "implicações", "discuta",
        "consequências", "compare", "avalie", "teoria",
        "metodologia", "framework", "arquitetura", "explique detalhadamente",
        "desenvolva", "elabore", "investigue", "explore"
    ]
    
    complex_score = sum(2 for indicator in complex_indicators if indicator in text_lower)
    if complex_score >= 4:
        model_scores["gpt"] += 4
        model_scores["deepseek"] += 3
    elif complex_score >= 2:
        model_scores["deepseek"] += 3
        model_scores["gpt"] += 2
        model_scores["gemini"] += 1
    
    # Análise de aspectos técnicos
    technical_indicators = [
        "código", "programação", "algoritmo", "função", "classe",
        "debug", "erro", "performance", "computação", "sistema",
        "protocolo", "implementação", "arquitetura", "tecnologia",
        "segurança", "criptografia", "desenvolvimento", "api",
        "banco de dados", "otimização"
    ]
    
    technical_score = sum(2 for indicator in technical_indicators if indicator in text_lower)
    if technical_score >= 6:
        model_scores["deepseek"] += 4
        model_scores["gpt"] += 3
    elif technical_score >= 3:
        model_scores["deepseek"] += 3
        model_scores["gpt"] += 2
        model_scores["gemini"] += 1

    # Análise de aspectos criativos e conversacionais
    creative_indicators = [
        "crie", "imagine", "sugira", "invente", "desenvolva",
        "história", "criativo", "inovador", "original", "ideia",
        "conceito", "design", "arte", "música", "poesia"
    ]
    
    creative_score = sum(2 for indicator in creative_indicators if indicator in text_lower)
    if creative_score >= 4:
        model_scores["mistral"] += 4
        model_scores["gemini"] += 3
    elif creative_score >= 2:
        model_scores["mistral"] += 3
        model_scores["gemini"] += 2

    # Análise de aspectos práticos e diretos
    practical_indicators = [
        "como fazer", "passo a passo", "exemplo", "explique",
        "mostre", "demonstre", "prático", "simples", "básico",
        "rápido", "fácil", "direto", "resumo", "síntese"
    ]
    
    practical_score = sum(2 for indicator in practical_indicators if indicator in text_lower)
    if practical_score >= 4:
        model_scores["mistral"] += 3
        model_scores["gemini"] += 3
    elif practical_score >= 2:
        model_scores["mistral"] += 2
        model_scores["gemini"] += 2
        model_scores["gpt"] += 1

    # Determina o modelo com maior pontuação
    recommended_model = max(model_scores.items(), key=lambda x: x[1])[0]
    max_score = max(model_scores.values())
    
    # Calcula a confiança baseada na diferença de pontuação
    scores = sorted(model_scores.values(), reverse=True)
    confidence = (scores[0] - scores[1]) / max(scores[0], 1)
    
    # Ajusta confiança para valores razoáveis
    confidence = min(max(confidence, 0.3), 0.9)
    
    return {
        "model": recommended_model,
        "task_type": task_type,
        "confidence": confidence,
        "metadata": {
            "complexity": complexity,
            "task_scores": task_keywords,
            "model_scores": model_scores,
            "complex_indicators_found": complex_score,
            "technical_indicators_found": technical_score,
            "creative_indicators_found": creative_score,
            "practical_indicators_found": practical_score
        }
    }