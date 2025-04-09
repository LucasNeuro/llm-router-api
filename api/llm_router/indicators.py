from typing import Dict, List, Set
import re
import string

def get_indicators(text: str) -> Dict[str, float]:
    """
    Analyze text and extract indicators for model selection.
    Returns a dictionary with indicator scores between 0 and 1.
    """
    # Normalize text
    text = text.lower().strip()
    
    # Initialize indicators
    indicators = {
        "complexity": 0.0,
        "technical": 0.0,
        "conversational": 0.0,
        "analytical": 0.0,
        "factual": 0.0,
        "creative": 0.0
    }
    
    # Word sets for different categories
    technical_words = {
        "código", "programa", "sistema", "tecnologia", "software",
        "hardware", "dados", "análise", "algoritmo", "computador",
        "desenvolvimento", "programação", "api", "banco de dados",
        "interface", "rede", "servidor", "aplicação", "framework"
    }
    
    analytical_words = {
        "analise", "compare", "explique", "porque", "como",
        "qual", "quais", "onde", "quando", "avalie",
        "considere", "examine", "investigue", "explore"
    }
    
    factual_words = {
        "fato", "verdade", "história", "evento", "data",
        "local", "pessoa", "número", "estatística", "informação",
        "definição", "exemplo", "caso", "situação"
    }
    
    creative_words = {
        "crie", "imagine", "desenvolva", "invente", "sugira",
        "proponha", "elabore", "desenhe", "planeje", "componha",
        "ideias", "criativo", "inovador", "original"
    }
    
    conversational_words = {
        "oi", "olá", "tudo bem", "como vai", "obrigado",
        "por favor", "tchau", "até logo", "bom dia", "boa tarde",
        "boa noite", "legal", "bacana", "beleza"
    }
    
    # Calculate word-based indicators
    words = set(text.split())
    
    indicators["technical"] = len(words.intersection(technical_words)) / len(technical_words)
    indicators["analytical"] = len(words.intersection(analytical_words)) / len(analytical_words)
    indicators["factual"] = len(words.intersection(factual_words)) / len(factual_words)
    indicators["creative"] = len(words.intersection(creative_words)) / len(creative_words)
    indicators["conversational"] = len(words.intersection(conversational_words)) / len(conversational_words)
    
    # Calculate complexity based on sentence length and unique words
    sentences = text.split(".")
    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
    unique_words_ratio = len(set(text.split())) / len(text.split())
    
    # Normalize complexity score between 0 and 1
    indicators["complexity"] = min((avg_sentence_length / 20) * unique_words_ratio, 1.0)
    
    return indicators 