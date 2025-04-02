from typing import Dict, Any, Optional
from .classifier_agent import classify_prompt
from .gpt import call_gpt
from .deepseek import call_deepseek
from .mistral import call_mistral
from .gemini import call_gemini
from api.utils.logger import logger

class LLMRouter:
    """Router para direcionar chamadas para diferentes modelos LLM"""
    
    async def route_prompt(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Roteia o prompt para o modelo apropriado e retorna a resposta"""
        try:
            # Se um modelo específico não foi fornecido, classifica o prompt
            if not model:
                classification = classify_prompt(prompt)
                model = classification["recommended_model"]
                logger.info(f"Modelo escolhido: {model}")
                logger.info(f"Pontuações: {classification['model_scores']}")
                logger.info(f"Indicadores: {classification['indicators']}")
            else:
                classification = {
                    "confidence": 1.0,
                    "model_scores": {model: 1.0},
                    "indicators": {
                        "complex": False,
                        "technical": False,
                        "analytical": False,
                        "simple": True
                    }
                }

            # Chama o modelo apropriado
            response = None
            if model == "gpt":
                response = await call_gpt(prompt)
            elif model == "deepseek":
                response = await call_deepseek(prompt)
            elif model == "mistral":
                response = await call_mistral(prompt)
            elif model == "gemini":
                response = await call_gemini(prompt)
            else:
                response = await call_gpt(prompt)  # GPT como fallback

            # Garante que a resposta seja uma string
            if not isinstance(response, str):
                response = str(response)

            # Retorna resposta com metadados
            return {
                "text": response,
                "model": model,
                "success": True,
                "confidence": classification.get("confidence", 0.0),
                "model_scores": classification.get("model_scores", {}),
                "indicators": classification.get("indicators", {})
            }
        
        except Exception as e:
            logger.error(f"Erro no router: {str(e)}")
            return {
                "text": f"Erro ao processar prompt: {str(e)}",
                "model": "error",
                "success": False,
                "confidence": 0.0,
                "model_scores": {},
                "indicators": {
                    "complex": False,
                    "technical": False,
                    "analytical": False,
                    "simple": True
                }
            }