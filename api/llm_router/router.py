from typing import Dict, Any, Optional
from .classifier_agent import classify_prompt
from .gpt import generate_response as call_gpt
from .deepseek import call_deepseek
from .mistral import call_mistral
from .gemini import call_gemini
from loguru import logger

class LLMRouter:
    """Classe responsável por rotear prompts para o modelo mais apropriado"""
    
    def __init__(self):
        self.models = {
            "gpt": call_gpt,
            "deepseek": call_deepseek,
            "mistral": call_mistral,
            "gemini": call_gemini
        }
        
    async def route_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Roteia o prompt para o modelo mais apropriado.
        
        Args:
            prompt: O texto do prompt
            model: Modelo específico a ser usado (opcional)
            **kwargs: Argumentos adicionais para a chamada do modelo
            
        Returns:
            Dict com a resposta e metadados
        """
        try:
            # Se um modelo específico foi solicitado, use-o
            if model and model in self.models:
                logger.info(f"Usando modelo específico: {model}")
                response = await self.models[model](prompt, **kwargs)
                # Garante que a resposta seja uma string
                if isinstance(response, dict):
                    response = response.get("text", str(response))
                return {
                    "text": str(response),
                    "model": model,
                    "success": True
                }
                
            # Caso contrário, use o classificador para escolher o modelo
            classification = classify_prompt(prompt)
            chosen_model = classification["model"]
            confidence = classification["confidence"]
            model_scores = classification["model_scores"]
            indicators = classification["indicators"]
            
            logger.info(f"Modelo escolhido: {chosen_model} (confiança: {confidence:.2f})")
            logger.info(f"Scores dos modelos: {model_scores}")
            logger.info(f"Indicadores: {indicators}")
            
            # Chama o modelo escolhido
            response = await self.models[chosen_model](prompt, **kwargs)
            # Garante que a resposta seja uma string
            if isinstance(response, dict):
                response = response.get("text", str(response))
            
            return {
                "text": str(response),
                "model": chosen_model,
                "success": True,
                "confidence": confidence,
                "model_scores": model_scores,
                "indicators": indicators
            }
            
        except Exception as e:
            logger.error(f"Erro ao rotear prompt: {str(e)}")
            return {
                "text": f"Erro ao processar prompt: {str(e)}",
                "model": model or "unknown",
                "success": False
            }