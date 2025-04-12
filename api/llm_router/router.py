from typing import Dict, Any, Optional, Callable, Awaitable
import json
from datetime import datetime
from api.utils.logger import logger
from .gemini import call_gemini
from .mistral import call_mistral
from .deepseek import call_deepseek
from .gpt import call_gpt
from .prompt_classifier import classify_prompt
from ..utils.cache_manager import cache_manager
from ..utils.conversation_memory import conversation_manager
from ..utils.audio_service import audio_service

class LLMRouter:
    """
    Router para LLMs com roteamento inteligente baseado em classificação de prompts
    """
    
    def __init__(self):
        """
        Inicializa o router com os modelos disponíveis.
        """
        # Define os modelos disponíveis
        self.models: Dict[str, Callable[[str], Awaitable[Dict[str, Any]]]] = {
            "gemini": call_gemini,
            "mistral": call_mistral,
            "deepseek": call_deepseek,
        }
        
        # Adiciona GPT apenas se tiver API key válida (reservado para áudio)
        from ..llm_router.gpt import GPT_API_KEY
        if GPT_API_KEY:
            self.models["gpt"] = call_gpt
            logger.info("GPT adicionado aos modelos disponíveis (reservado para áudio)")
        else:
            logger.warning("GPT não disponível - API key não configurada")
            
        # Define a ordem de fallback para quando um modelo falha
        self.fallback_order = ["deepseek", "mistral", "gemini", "gpt"]
        
        logger.info(f"LLM Router inicializado com {len(self.models)} modelos: {', '.join(self.models.keys())}")
        
    async def _try_model_with_fallback(self, model_name: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Tenta usar um modelo com fallback para outros modelos em caso de falha
        
        Args:
            model_name: Nome do modelo a ser usado
            prompt: Texto do prompt
            **kwargs: Argumentos adicionais para a chamada
            
        Returns:
            Resposta do modelo com informações sobre fallback
        """
        used_models = []
        current_model = model_name
        
        # Tenta o modelo solicitado e depois segue a ordem de fallback
        while True:
            if current_model not in self.models:
                # Pula este modelo se não estiver disponível
                logger.warning(f"Modelo {current_model} não está disponível, pulando")
                used_models.append({"model": current_model, "status": "unavailable"})
            else:
                try:
                    # Tenta chamar o modelo atual
                    logger.info(f"Tentando modelo: {current_model}")
                    response = await self.models[current_model](prompt, **kwargs)
                    
                    # Se chegou aqui, a chamada foi bem-sucedida
                    used_models.append({"model": current_model, "status": "success"})
                    
                    # Garante que a resposta é um dicionário e tem um campo "text"
                    if isinstance(response, dict):
                        if "text" not in response:
                            response["text"] = f"Resposta sem texto do modelo {current_model}"
                    else:
                        response = {"text": str(response)}
                    
                    # Adiciona informações sobre o processo de fallback
                    response["model"] = current_model
                    response["original_model"] = model_name
                    response["used_fallback"] = current_model != model_name
                    response["fallback_info"] = used_models
                    
                    return response
                    
                except Exception as e:
                    # Registra a falha para este modelo
                    logger.error(f"Erro ao chamar modelo {current_model}: {str(e)}")
                    used_models.append({"model": current_model, "status": "error", "error": str(e)})
            
            # Tenta o próximo modelo na ordem de fallback
            try:
                # Remove os modelos já tentados da lista de fallback
                fallback_options = [m for m in self.fallback_order if m not in [u["model"] for u in used_models]]
                
                if not fallback_options:
                    # Não há mais modelos para tentar
                    logger.error("Todos os modelos falharam, não há mais fallbacks disponíveis")
                    raise ValueError("Todos os modelos de fallback falharam")
                
                current_model = fallback_options[0]
                logger.info(f"Fallback para modelo: {current_model}")
                
            except Exception as e:
                # Se não houver mais modelos de fallback, retorna erro
                logger.error(f"Erro no processo de fallback: {str(e)}")
                return {
                    "text": f"Erro em todos os modelos disponíveis. Por favor, tente novamente mais tarde.",
                    "model": "fallback_error",
                    "original_model": model_name,
                    "success": False,
                    "used_fallback": True,
                    "fallback_info": used_models
        }
        
    async def route_prompt(
        self,
        prompt: str,
        sender_phone: Optional[str] = None,
        model: Optional[str] = None,
        use_cache: bool = True,
        generate_audio: bool = False,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Roteia o prompt para o modelo mais apropriado.
        
        Args:
            prompt: O texto do prompt
            sender_phone: Número do remetente para contexto
            model: Modelo específico a ser usado (opcional)
            use_cache: Se deve usar o cache
            generate_audio: Se deve gerar áudio da resposta
            **kwargs: Argumentos adicionais para a chamada do modelo
            
        Returns:
            Dict com a resposta e metadados
        """
        try:
            logger.info(f"Iniciando roteamento para sender_phone: {sender_phone}")
            logger.info(f"Prompt recebido: {prompt}")
            
            # Se for solicitado geração de áudio, usa prioritariamente o GPT
            if generate_audio and "gpt" in self.models:
                logger.info("Geração de áudio solicitada, usando GPT prioritariamente")
                model = "gpt"
            
            # Adiciona mensagem do usuário à memória
            if sender_phone:
                logger.info("Adicionando mensagem do usuário à memória")
                await conversation_manager.add_message(
                    sender_phone=sender_phone,
                    role="user",
                    content=prompt,
                    save_to_db=True
                )
            
            # Verifica cache primeiro
            if use_cache:
                cached_response = await cache_manager.get_cached_response(prompt)
                if cached_response:
                    logger.info("Resposta encontrada no cache")
                    
                    # Adiciona resposta do cache à memória
                    if sender_phone:
                        await conversation_manager.add_message(
                            sender_phone=sender_phone,
                            role="assistant",
                            content=cached_response["text"],
                            model_used=cached_response["model"],
                            save_to_db=True
                        )
                    
                    # Se precisar gerar áudio, gera a partir do texto do cache
                    audio_info = None
                    if generate_audio:
                        logger.info("Gerando áudio para resposta do cache")
                        try:
                            audio_result = await audio_service.text_to_speech(
                                text=cached_response["text"],
                                request_id=str(datetime.utcnow().timestamp())
                            )
                            audio_info = audio_result
                        except Exception as audio_error:
                            logger.error(f"Erro ao gerar áudio: {str(audio_error)}")
                    
                    result = {
                        "text": cached_response["text"],
                        "model": cached_response["model"],
                        "success": True,
                        "from_cache": True,
                        "cache_info": {
                            "hit_count": cached_response.get("hit_count", 1),
                            "cached_at": cached_response.get("created_at", datetime.utcnow().isoformat()),
                            "last_accessed": cached_response.get("last_accessed", datetime.utcnow().isoformat())
                        },
                        "has_memory": bool(sender_phone)
                    }
                    
                    # Adiciona informações de áudio ao resultado se gerado
                    if audio_info:
                        result["audio"] = audio_info
                    
                    return result
            
            # Se um modelo específico foi solicitado
            if model:
                # Verifica se o modelo solicitado existe
                if model not in self.models and model not in self.fallback_order:
                    logger.warning(f"Modelo solicitado '{model}' não existe, usando classificação automática")
                    model = None
                else:
                    # Chama o modelo com fallback automático
                    response = await self._try_model_with_fallback(model, prompt, **kwargs)
                    
                    # Adiciona resposta à memória
                    if sender_phone:
                        await conversation_manager.add_message(
                            sender_phone=sender_phone,
                            role="assistant",
                            content=response["text"],
                            model_used=response["model"],
                            save_to_db=True
                        )
                    
                    # Gera áudio se solicitado
                    audio_info = None
                    if generate_audio:
                        try:
                            audio_result = await audio_service.text_to_speech(
                                text=response["text"],
                                request_id=str(datetime.utcnow().timestamp())
                            )
                            audio_info = audio_result
                        except Exception as audio_error:
                            logger.error(f"Erro ao gerar áudio: {str(audio_error)}")
                    
                    result = {
                        "text": response["text"],
                        "model": response["model"],
                        "success": True,
                        "from_cache": False,
                        "has_memory": bool(sender_phone)
                    }
                    
                    # Adiciona informações de áudio ao resultado se gerado
                    if audio_info:
                        result["audio"] = audio_info
                    
                    # Salva no cache
                    if use_cache:
                        await cache_manager.cache_response(prompt, result, response["model"])
                    
                    return result
            
            # Se não foi especificado um modelo, usa classificação automática
            classification = await classify_prompt(prompt)
            chosen_model = classification["best_model"]
            confidence = classification["confidence"]
            model_scores = classification["model_scores"]
            indicators = classification["indicators"]
            
            logger.info(f"Classificação: modelo={chosen_model}, confiança={confidence}")
            
            # Chama o modelo escolhido com fallback automático
            response = await self._try_model_with_fallback(chosen_model, prompt, **kwargs)
            response_text = response["text"]
            used_model = response["model"]
            used_fallback = response.get("used_fallback", False)
            
            # Adiciona resposta à memória
            if sender_phone:
                await conversation_manager.add_message(
                    sender_phone=sender_phone,
                    role="assistant",
                    content=response_text,
                    model_used=used_model,
                    save_to_db=True
                )
            
            # Gera áudio se solicitado
            audio_info = None
            if generate_audio:
                try:
                    audio_result = await audio_service.text_to_speech(
                        text=response_text,
                        request_id=str(datetime.utcnow().timestamp())
                    )
                    audio_info = audio_result
                except Exception as audio_error:
                    logger.error(f"Erro ao gerar áudio: {str(audio_error)}")
            
            result = {
                "text": response_text,
                "model": used_model,
                "classified_model": chosen_model,
                "confidence": confidence,
                "model_scores": model_scores,
                "indicators": indicators,
                "used_fallback": used_fallback,
                "fallback_info": response.get("fallback_info", []),
                "success": True,
                "from_cache": False,
                "has_memory": bool(sender_phone)
            }
            
            # Adiciona informações de áudio ao resultado se gerado
            if audio_info:
                result["audio"] = audio_info
            
            # Salva no cache
            if use_cache:
                await cache_manager.cache_response(prompt, result, used_model)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro no roteamento: {str(e)}")
            logger.exception("Stacktrace completo:")
            raise