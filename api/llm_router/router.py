from typing import Dict, Any, Optional
from .classifier_agent import classify_prompt
from .gpt import generate_response as call_gpt
from .deepseek import call_deepseek
from .mistral import call_mistral
from .gemini import call_gemini
from loguru import logger
from api.utils.conversation_memory import conversation_manager
from api.utils.cache_manager import cache_manager
import json

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
        sender_phone: Optional[str] = None,
        model: Optional[str] = None,
        use_cache: bool = True,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Roteia o prompt para o modelo mais apropriado.
        
        Args:
            prompt: O texto do prompt
            sender_phone: Número do remetente para contexto
            model: Modelo específico a ser usado (opcional)
            use_cache: Se deve usar o cache
            **kwargs: Argumentos adicionais para a chamada do modelo
            
        Returns:
            Dict com a resposta e metadados
        """
        try:
            logger.info(f"Iniciando roteamento para sender_phone: {sender_phone}")
            logger.info(f"Prompt recebido: {prompt}")
            
            # Verifica cache primeiro
            if use_cache:
                cached_response = await cache_manager.get_cached_response(prompt)
                if cached_response:
                    logger.info("Resposta encontrada no cache")
                    # Adiciona à memória de conversa se tiver sender_phone
                    if sender_phone:
                        await conversation_manager.add_message(
                            sender_phone=sender_phone,
                            role="user",
                            content=prompt,
                            save_to_db=True
                        )
                        await conversation_manager.add_message(
                            sender_phone=sender_phone,
                            role="assistant",
                            content=cached_response["text"],
                            model_used=cached_response["model"],
                            save_to_db=True
                        )
                    return cached_response

            # Adiciona mensagem do usuário à memória
            if sender_phone:
                logger.info("Adicionando mensagem do usuário à memória")
                await conversation_manager.add_message(
                    sender_phone=sender_phone,
                    role="user",
                    content=prompt,
                    save_to_db=True
                )
                
                # Recupera contexto da conversa
                context = await conversation_manager.format_conversation_for_llm(sender_phone)
                full_prompt = f"{context}\n\nNova mensagem: {prompt}"
                logger.info(f"Prompt com contexto: {full_prompt}")
            else:
                logger.info("Sem sender_phone, usando prompt sem contexto")
                full_prompt = prompt

            # Se um modelo específico foi solicitado, use-o
            if model and model in self.models:
                logger.info(f"Usando modelo específico: {model}")
                response = await self.models[model](full_prompt, **kwargs)
                # Garante que a resposta seja uma string
                if isinstance(response, dict):
                    response = response.get("text", str(response))
                
                result = {
                    "text": str(response),
                    "model": model,
                    "success": True
                }
                
                # Salva no cache
                if use_cache:
                    await cache_manager.cache_response(prompt, result, model)
                
                # Adiciona resposta do assistente à memória
                if sender_phone:
                    logger.info("Salvando resposta do assistente na memória")
                    await conversation_manager.add_message(
                        sender_phone=sender_phone,
                        role="assistant",
                        content=response,
                        model_used=model,
                        save_to_db=True
                    )
                
                return result
                
            # Caso contrário, use o classificador para escolher o modelo
            classification = classify_prompt(prompt)
            chosen_model = classification["model"]
            confidence = classification["confidence"]
            model_scores = classification["model_scores"]
            indicators = classification["indicators"]
            
            logger.info(f"Modelo escolhido: {chosen_model} (confiança: {confidence:.2f})")
            logger.info(f"Scores dos modelos: {json.dumps(model_scores, indent=2)}")
            logger.info(f"Indicadores: {json.dumps(indicators, indent=2)}")
            
            # Chama o modelo escolhido
            try:
                response = await self.models[chosen_model](full_prompt, **kwargs)
                # Garante que a resposta seja uma string
                if isinstance(response, dict):
                    response = response.get("text", str(response))
                
                result = {
                    "text": str(response),
                    "model": chosen_model,
                    "success": True,
                    "confidence": confidence,
                    "model_scores": model_scores,
                    "indicators": indicators,
                    "has_context": bool(context) if 'context' in locals() else False
                }
                
                # Salva no cache apenas se a resposta for bem sucedida
                if use_cache and result["success"]:
                    await cache_manager.cache_response(prompt, result, chosen_model)
                
                # Adiciona resposta do assistente à memória apenas se for bem sucedida
                if sender_phone and result["success"]:
                    logger.info("Salvando resposta do assistente na memória")
                    await conversation_manager.add_message(
                        sender_phone=sender_phone,
                        role="assistant",
                        content=response,
                        model_used=chosen_model,
                        save_to_db=True
                    )
                
                return result
                
            except Exception as e:
                error_msg = f"Erro ao chamar modelo {chosen_model}: {str(e)}"
                logger.error(error_msg)
                return {
                    "text": error_msg,
                    "model": chosen_model,
                    "success": False,
                    "confidence": confidence,
                    "model_scores": model_scores,
                    "indicators": indicators
                }

        except Exception as e:
            logger.error(f"Erro ao rotear prompt: {str(e)}")
            logger.exception("Stacktrace completo:")
            return {
                "text": f"Erro ao processar prompt: {str(e)}",
                "model": model or "unknown",
                "success": False
            }