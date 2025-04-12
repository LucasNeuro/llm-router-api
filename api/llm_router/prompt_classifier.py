from typing import Dict, Any
import re
import json
from api.utils.logger import logger
from ..llm_router.gpt import GPT_API_KEY

def classify_prompt(prompt: str) -> Dict[str, Any]:
    """
    Classifica um prompt para determinar qual modelo deve ser usado
    
    Args:
        prompt: O texto do prompt
        
    Returns:
        Dicionário com:
        - model: Nome do modelo escolhido
        - confidence: Confiança na escolha (0.0 a 1.0)
        - model_scores: Scores para cada modelo
        - indicators: Indicadores detectados
    """
    # Inicializa os scores com base nas características dos modelos
    model_scores = {
        "gemini": 0.2,   # Bom para conversação geral
        "mistral": 0.3,  # Melhor para análise e técnico
        "deepseek": 0.3  # Melhor para complexidade
    }
    
    # Adiciona GPT apenas se estiver disponível
    if GPT_API_KEY:
        model_scores["gpt"] = 0.1  # Score inicial baixo
    
    # Detecta os indicadores
    indicators = {
        "complex": is_complex(prompt),
        "technical": is_technical(prompt),
        "analytical": is_analytical(prompt),
        "simple": is_simple(prompt),
        "audio_related": is_audio_related(prompt)
    }
    
    logger.info(f"Indicadores detectados: {json.dumps(indicators, indent=2)}")
    
    # Ajusta scores com base nos indicadores
    if indicators["complex"]:
        model_scores["deepseek"] += 0.4
        model_scores["mistral"] += 0.2
        model_scores["gemini"] -= 0.1
        
    if indicators["technical"]:
        model_scores["mistral"] += 0.4
        model_scores["deepseek"] += 0.3
        model_scores["gemini"] -= 0.1
        
    if indicators["analytical"]:
        model_scores["mistral"] += 0.3
        model_scores["deepseek"] += 0.3
        model_scores["gemini"] += 0.1
        
    if indicators["simple"]:
        model_scores["gemini"] += 0.4
        model_scores["mistral"] += 0.1
        model_scores["deepseek"] -= 0.1
    
    # Ajuste especial para GPT se disponível
    if "gpt" in model_scores:
        if indicators["audio_related"]:
            model_scores["gpt"] += 0.5
        if indicators["complex"] or indicators["analytical"]:
            model_scores["gpt"] += 0.2
    
    # Garante que todos os scores sejam positivos
    model_scores = {k: max(v, 0.1) for k, v in model_scores.items()}
    
    # Normaliza os scores
    total_score = sum(model_scores.values())
    model_scores = {model: score / total_score for model, score in model_scores.items()}
    
    # Escolhe o modelo com maior score
    chosen_model = max(model_scores.items(), key=lambda x: x[1])
    model_name = chosen_model[0]
    confidence = chosen_model[1]
    
    logger.info(f"Scores dos modelos: {json.dumps(model_scores, indent=2)}")
    logger.info(f"Modelo escolhido: {model_name} com confiança {confidence:.2f}")
    
    return {
        "model": model_name,
        "confidence": confidence,
        "model_scores": model_scores,
        "indicators": indicators
    }

def is_complex(prompt: str) -> bool:
    """Verifica se o prompt é complexo"""
    # Indicadores de complexidade
    indicators = [
        len(prompt) > 150,  # Prompt longo
        len(prompt.split()) > 30,  # Muitas palavras
        len(re.findall(r'[.!?]', prompt)) > 2,  # Múltiplas frases
        any(word in prompt.lower() for word in [
            "explique", "compare", "analise", "avalie",
            "discuta", "relacione", "demonstre", "argumente",
            "teoria", "conceito", "princípio", "metodologia"
        ])
    ]
    return sum(indicators) >= 2  # Se pelo menos 2 indicadores forem verdadeiros

def is_technical(prompt: str) -> bool:
    """Verifica se o prompt é técnico"""
    technical_terms = [
        "algoritmo", "função", "código", "programação",
        "física", "química", "matemática", "equação",
        "teoria", "tecnologia", "sistema", "processo",
        "método", "análise", "estrutura", "framework",
        "implementação", "desenvolvimento", "arquitetura",
        "protocolo", "metodologia", "técnica"
    ]
    
    # Conta quantos termos técnicos aparecem
    term_count = sum(1 for term in technical_terms if term in prompt.lower())
    return term_count >= 1

def is_analytical(prompt: str) -> bool:
    """Verifica se o prompt requer análise"""
    analytical_indicators = [
        "compare", "analise", "avalie", "discuta",
        "explique", "justifique", "demonstre",
        "impactos", "consequências", "benefícios",
        "vantagens", "desvantagens", "diferenças",
        "semelhanças", "relação", "correlação"
    ]
    
    # Conta indicadores analíticos
    indicator_count = sum(1 for ind in analytical_indicators if ind in prompt.lower())
    return indicator_count >= 1

def is_simple(prompt: str) -> bool:
    """Verifica se o prompt é simples"""
    # Indicadores de simplicidade
    indicators = [
        len(prompt) < 100,  # Prompt curto
        len(prompt.split()) < 20,  # Poucas palavras
        len(re.findall(r'[.!?]', prompt)) <= 1,  # Uma frase ou menos
        not is_complex(prompt),  # Não é complexo
        not is_technical(prompt),  # Não é técnico
        not is_analytical(prompt)  # Não é analítico
    ]
    return sum(indicators) >= 3  # Se pelo menos 3 indicadores forem verdadeiros

def is_audio_related(prompt: str) -> bool:
    """Verifica se o prompt está relacionado a áudio"""
    audio_terms = [
        "áudio", "som", "voz", "fala", "escuta",
        "ouvir", "escutar", "música", "sonoro",
        "grave", "agudo", "melodia", "volume"
    ]
    return any(term in prompt.lower() for term in audio_terms) 