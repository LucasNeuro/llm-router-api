from typing import Dict, Any, Optional
from .deepseek import call_deepseek
from .gemini import call_gemini
from .mistral import call_mistral
from .gpt import call_gpt
from .classifier_agent import classify_prompt
from api.utils.logger import logger

# System prompts padrão para cada modelo
DEFAULT_SYSTEM_PROMPTS = {
    "gpt": "Você é um assistente prestativo e amigável.",
    "gemini": "Você é um assistente prestativo e amigável.",
    "mistral": "Você é um assistente prestativo e amigável.",
    "deepseek": "Você é um assistente prestativo e amigável."
}

class LLMRouter:
    """
    Router para direcionar chamadas para diferentes modelos LLM
    """
    
    async def route_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Roteia o prompt para o modelo apropriado
        """
        try:
            # Se nenhum modelo foi especificado, usa o classificador
            if not model:
                model = await classify_prompt(prompt)
            
            # Usa o system prompt padrão se nenhum foi fornecido
            if not system_prompt:
                system_prompt = DEFAULT_SYSTEM_PROMPTS.get(model)
            
            # Roteia para o modelo apropriado
            if model == "gpt":
                return await call_gpt(prompt, system_prompt)
            elif model == "gemini":
                return await call_gemini(prompt, system_prompt)
            elif model == "mistral":
                return await call_mistral(prompt, system_prompt)
            elif model == "deepseek":
                return await call_deepseek(prompt, system_prompt)
            else:
                error_msg = f"Modelo {model} não suportado"
                return {
                    "text": error_msg,
                    "model": "error",
                    "success": False
                }
                
        except Exception as e:
            error_msg = f"Erro ao rotear prompt: {str(e)}"
            return {
                "text": error_msg,
                "model": "error",
                "success": False
            }