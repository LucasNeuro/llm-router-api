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
from ..utils.audio_service import audio_service, AudioService
from ..utils.supabase import supabase, save_llm_data

class PersonaConfig:
    """Configuração da persona do assistente"""
    
    # Vozes disponíveis na OpenAI
    VOICES = {
        "ALLOY": "alloy",      # Voz neutra e profissional
        "ECHO": "echo",        # Voz mais suave e acolhedora
        "FABLE": "fable",      # Voz mais jovem e animada
        "ONYX": "onyx",        # Voz mais grave e confiante
        "NOVA": "nova",        # Voz mais natural e conversacional
        "SHIMMER": "shimmer"   # Voz mais clara e articulada
    }
    
    # Personas pré-definidas
    PERSONAS = {
        "AMIGAVEL": {
            "voice": VOICES["NOVA"],
            "description": "Assistente amigável e acolhedor, usa linguagem informal e emojis",
            "personality_prompt": """
                Você é um assistente amigável e acolhedor. Use uma linguagem informal e natural.
                Adicione emojis ocasionalmente para tornar a conversa mais leve.
                Evite linguagem muito técnica, prefira explicações simples e diretas.
                Seja empático e mostre interesse genuíno nas questões do usuário.
            """
        },
        "PROFISSIONAL": {
            "voice": VOICES["ALLOY"],
            "description": "Assistente profissional e objetivo, mantém formalidade adequada",
            "personality_prompt": """
                Você é um assistente profissional e objetivo.
                Use linguagem clara e formal, mas não excessivamente técnica.
                Mantenha um tom respeitoso e profissional.
                Foque em respostas precisas e bem estruturadas.
            """
        },
        "ESPECIALISTA": {
            "voice": VOICES["ONYX"],
            "description": "Especialista técnico com profundo conhecimento",
            "personality_prompt": """
                Você é um especialista com profundo conhecimento técnico.
                Use termos técnicos quando apropriado, mas saiba explicá-los.
                Mantenha um tom confiante e assertivo.
                Forneça explicações detalhadas quando necessário.
            """
        }
    }
    
    @staticmethod
    def get_persona_prompt(persona_type: str) -> str:
        """Retorna o prompt de personalidade para a persona selecionada"""
        persona = PersonaConfig.PERSONAS.get(persona_type.upper())
        if not persona:
            # Se não encontrar, usa a persona amigável como padrão
            return PersonaConfig.PERSONAS["AMIGAVEL"]["personality_prompt"]
        return persona["personality_prompt"]
    
    @staticmethod
    def get_voice(persona_type: str) -> str:
        """Retorna a voz para a persona selecionada"""
        persona = PersonaConfig.PERSONAS.get(persona_type.upper())
        if not persona:
            # Se não encontrar, usa a voz nova como padrão
            return PersonaConfig.VOICES["NOVA"]
        return persona["voice"]

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
        
        self.current_persona = "AMIGAVEL"  # Persona padrão
        
    def set_persona(self, persona_type: str):
        """Define a persona atual"""
        if persona_type.upper() in PersonaConfig.PERSONAS:
            self.current_persona = persona_type.upper()
            logger.info(f"Persona alterada para: {self.current_persona}")
        
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
                    
                    # Se precisar gerar áudio, gera a partir do texto do cache
                    audio_info = None
                    if generate_audio:
                        logger.info("Gerando áudio para resposta do cache")
                        audio_info = await audio_service.text_to_speech(
                            cached_response["text"],
                            sender_phone=sender_phone
                        )
                        
                        # Salva metadados do áudio vinculados ao sender_phone
                        if audio_info["success"] and sender_phone:
                            conversation_id = await conversation_manager.get_conversation_id(sender_phone)
                            await audio_service.save_audio_metadata(audio_info, conversation_id)
                    
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
                    if generate_audio and audio_info and audio_info["success"]:
                        audio_base64 = await audio_service.get_audio_base64(audio_info["local_path"])
                        if audio_base64:
                            result["audio"] = {
                                "data": audio_base64,
                                "format": "mp3",
                                "base64": True,
                                "url": audio_info["url"]
                            }
                        # Limpa arquivo temporário
                        audio_service.cleanup_temp_file(audio_info["local_path"])
                        
                    return result

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

            # Se um modelo específico foi solicitado
            if model:
                # Verifica se o modelo solicitado existe em alguma forma
                model_exists = model in self.models or model in self.fallback_order
                
                if not model_exists:
                    logger.warning(f"Modelo solicitado '{model}' não existe, usando classificação automática")
                    model = None
                else:
                    # Chama o modelo com fallback automático
                    response = await self._try_model_with_fallback(model, full_prompt, **kwargs)
                    chosen_model = response["model"]
                    response_text = response["text"]
                    used_fallback = response.get("used_fallback", False)
                    
                    logger.info(f"Modelo usado: {chosen_model} (solicitado: {model}, fallback: {used_fallback})")
                    
                    # Gera áudio se solicitado
                    audio_info = None
                    if generate_audio:
                        logger.info(f"Gerando áudio para resposta do modelo {chosen_model}")
                        audio_info = await audio_service.text_to_speech(
                            response_text,
                            sender_phone=sender_phone
                        )
                        
                        # Salva metadados do áudio vinculados ao sender_phone
                        if audio_info["success"] and sender_phone:
                            conversation_id = await conversation_manager.get_conversation_id(sender_phone)
                            await audio_service.save_audio_metadata(audio_info, conversation_id)
                    
                    result = {
                        "text": response_text,
                        "model": chosen_model,
                        "requested_model": model,  # Modelo originalmente solicitado
                        "used_fallback": used_fallback,
                        "fallback_info": response.get("fallback_info", []),
                        "success": True,
                        "from_cache": False,
                        "has_memory": bool(sender_phone)
                    }
                    
                    # Adiciona informações de áudio ao resultado se gerado
                    if generate_audio and audio_info and audio_info["success"]:
                        audio_base64 = await audio_service.get_audio_base64(audio_info["local_path"])
                        if audio_base64:
                            result["audio"] = {
                                "data": audio_base64,
                                "format": "mp3",
                                "base64": True,
                                "url": audio_info["url"]
                            }
                        # Limpa arquivo temporário
                        audio_service.cleanup_temp_file(audio_info["local_path"])
                    
                    # Salva no cache
                    if use_cache:
                        await cache_manager.cache_response(prompt, result, chosen_model)
                    
                    # Adiciona resposta do assistente à memória
                    if sender_phone:
                        logger.info("Salvando resposta do assistente na memória")
                        await conversation_manager.add_message(
                            sender_phone=sender_phone,
                            role="assistant",
                            content=response_text,
                            model_used=chosen_model,
                            save_to_db=True
                        )
                    
                    return result
                
            # Caso contrário, use o classificador para escolher o modelo
            classification = classify_prompt(prompt)
            chosen_model = classification["model"]
            confidence = classification["confidence"]
            model_scores = classification["model_scores"]
            indicators = classification["indicators"]
            
            logger.info(f"Modelo escolhido pelo classificador: {chosen_model} (confiança: {confidence:.2f})")
            logger.info(f"Scores dos modelos: {json.dumps(model_scores, indent=2)}")
            logger.info(f"Indicadores: {json.dumps(indicators, indent=2)}")
            
            # Chama o modelo escolhido com fallback automático
            response = await self._try_model_with_fallback(chosen_model, full_prompt, **kwargs)
            used_model = response["model"]
            response_text = response["text"]
            used_fallback = response.get("used_fallback", False)
            
            logger.info(f"Modelo efetivamente usado: {used_model} (classificado: {chosen_model}, fallback: {used_fallback})")
            
            # Gera áudio se solicitado
            audio_info = None
            if generate_audio:
                logger.info(f"Gerando áudio para resposta do modelo {used_model}")
                audio_info = await audio_service.text_to_speech(
                    response_text,
                    sender_phone=sender_phone
                )
                
                # Salva metadados do áudio vinculados ao sender_phone
                if audio_info["success"] and sender_phone:
                    conversation_id = await conversation_manager.get_conversation_id(sender_phone)
                    await audio_service.save_audio_metadata(audio_info, conversation_id)
            
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
            if generate_audio and audio_info and audio_info["success"]:
                audio_base64 = await audio_service.get_audio_base64(audio_info["local_path"])
                if audio_base64:
                    result["audio"] = {
                        "data": audio_base64,
                        "format": "mp3",
                        "base64": True,
                        "url": audio_info["url"]
                    }
                # Limpa arquivo temporário
                audio_service.cleanup_temp_file(audio_info["local_path"])
            
            # Salva no cache
            if use_cache:
                await cache_manager.cache_response(prompt, result, used_model)
            
            # Adiciona resposta do assistente à memória
            if sender_phone:
                logger.info("Salvando resposta do assistente na memória")
                await conversation_manager.add_message(
                    sender_phone=sender_phone,
                    role="assistant",
                    content=response_text,
                    model_used=used_model,
                    save_to_db=True
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao rotear prompt: {str(e)}")
            logger.exception("Stacktrace completo:")
            return {
                "text": f"Erro ao processar prompt: {str(e)}",
                "model": model or "unknown",
                "success": False,
                "from_cache": False,
                "has_memory": bool(sender_phone)
            }

    async def _generate_response(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera resposta usando o modelo especificado
        TODO: Implementar integração com diferentes modelos
        """
        # Placeholder - implementar integração real
        return {
            "text": "Esta é uma resposta de exemplo.",
            "request_id": "123",
            "model_used": model or "default"
            }