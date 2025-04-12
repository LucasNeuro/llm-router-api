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
    # Inicializa os scores
    model_scores = {
        "gemini": 0.3,  # Default score
        "mistral": 0.3, # Default score
        "deepseek": 0.3 # Default score
    }
    
    # Adiciona GPT apenas se estiver disponível (mas com score baixo, pois é reservado para áudio)
    if GPT_API_KEY:
        model_scores["gpt"] = 0.1  # Score mais baixo pois é reservado para áudio
    
    # Se o prompt menciona explicitamente áudio, aumenta o score do GPT
    if ("áudio" in prompt.lower() or "ouvir" in prompt.lower() or 
        "escutar" in prompt.lower() or "voz" in prompt.lower() or
        "som" in prompt.lower()):
        model_scores["gpt"] = model_scores.get("gpt", 0) + 0.4
        
    # Indicadores para análise do prompt
    indicators = {
        "complex": is_complex(prompt),
        "technical": is_technical(prompt),
        "analytical": is_analytical(prompt),
        "simple": is_simple(prompt),
        "audio_related": is_audio_related(prompt)
    }
    
    # Calcula scores com base nos indicadores
    if indicators["complex"]:
        model_scores["deepseek"] = model_scores.get("deepseek", 0) + 0.3
        if "gpt" in model_scores:
            model_scores["gpt"] += 0.2
        
    if indicators["technical"]:
        model_scores["mistral"] = model_scores.get("mistral", 0) + 0.3
        model_scores["deepseek"] = model_scores.get("deepseek", 0) + 0.2
        
    if indicators["analytical"]:
        if "gpt" in model_scores:
            model_scores["gpt"] += 0.1
        model_scores["deepseek"] = model_scores.get("deepseek", 0) + 0.2
        
    if indicators["simple"]:
        model_scores["gemini"] = model_scores.get("gemini", 0) + 0.3
        model_scores["mistral"] = model_scores.get("mistral", 0) + 0.2
        
    if indicators["audio_related"] and "gpt" in model_scores:
        model_scores["gpt"] += 0.4  # Boost substancial para GPT se relacionado a áudio
        
    # Normaliza os scores
    total_score = sum(model_scores.values())
    model_scores = {model: score / total_score for model, score in model_scores.items()}
    
    # Escolhe o modelo com maior score
    chosen_model = max(model_scores.items(), key=lambda x: x[1])
    model_name = chosen_model[0]
    confidence = chosen_model[1]
    
    logger.info(f"Prompt classificado: modelo={model_name}, confiança={confidence:.2f}")
    
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
        len(prompt) > 300,  # Prompt longo
        len(prompt.split()) > 50,  # Muitas palavras
        len(re.findall(r'[.!?]', prompt)) > 3,  # Múltiplas frases
        any(term in prompt.lower() for term in [
            "explique", "detalhe", "análise", "compare", "contraste",
            "discuta", "avalie", "critique", "sintetize", "filosófico",
            "profund", "complex", "abrangente"
        ])
    ]
    
    return sum(indicators) >= 2  # Se pelo menos 2 indicadores forem verdadeiros

def is_technical(prompt: str) -> bool:
    """Verifica se o prompt é técnico"""
    # Termos técnicos para diferentes áreas
    technical_terms = [
        # Programação/Tecnologia
        "código", "programa", "função", "api", "algoritmo", "cloud", "aws", "azure",
        "docker", "kubernetes", "linux", "servidor", "frontend", "backend", "devops",
        "javascript", "python", "java", "c++", "sql", "banco de dados", "framework",
        
        # Ciência
        "física", "química", "biologia", "matemática", "equação", "fórmula",
        "científic", "quantum", "átomo", "molecular", "genética", "célula",
        
        # Medicina
        "médic", "clínic", "doença", "patologia", "diagnóstico", "tratamento",
        "anatomia", "fisiologia", "cirurgia", "farmacologia", "terapia",
        
        # Finanças/Economia
        "finanças", "economi", "contabilidade", "mercado", "ações", "investimento",
        "bolsa", "taxa", "juros", "fiscal", "tributári", "imposto", "lucro", "custo",
        
        # Engenharia
        "engenhari", "estrutura", "mecânica", "elétrica", "civil", "construção",
        "projeto", "design", "cad", "material", "resistência", "torque"
    ]
    
    # Verifica se há termos técnicos no prompt
    prompt_lower = prompt.lower()
    matches = [term for term in technical_terms if term in prompt_lower]
    
    return len(matches) >= 1

def is_analytical(prompt: str) -> bool:
    """Verifica se o prompt requer análise ou pensamento crítico"""
    analytical_indicators = [
        "analis", "compar", "contrast", "avali", "critic", "pros e contras",
        "vantagens", "desvantagens", "melhor", "pior", "recomend", "aconselharia",
        "por que", "razão", "causa", "efeito", "impacto", "consequência",
        "evidência", "argumento", "justific", "demonstr", "prov"
    ]
    
    prompt_lower = prompt.lower()
    matches = [indicator for indicator in analytical_indicators if indicator in prompt_lower]
    
    return len(matches) >= 1

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
    audio_indicators = [
        "áudio", "ouvir", "escutar", "voz", "som", "narração", "narrar",
        "canção", "música", "falar", "pronuncia", "sotaque", "falando",
        "grave", "agudo", "timbre", "entonação", "dicção", "cantado",
        "melodia", "speaker", "fone", "alto-falante", "rádio", "podcasts",
        "audiobook", "livro falado", "dublagem", "tonalidade", "sonoro"
    ]
    
    prompt_lower = prompt.lower()
    matches = [indicator for indicator in audio_indicators if indicator in prompt_lower]
    
    return len(matches) >= 1 