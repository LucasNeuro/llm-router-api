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
        Roteia um prompt para o modelo mais apropriado
        """
        try:
            # Se for para gerar áudio, usa o GPT diretamente
            if generate_audio and "gpt" in self.models:
                model = "gpt"
                logger.info("Usando GPT para geração de áudio")
            
            # Se não tiver modelo específico, classifica o prompt
            if not model:
                classification = await classify_prompt(prompt)
                model = classification["best_model"]
                logger.info(f"Modelo escolhido por classificação: {model}")
            
            # Verifica cache se habilitado
            if use_cache:
                cached = await cache_manager.get_cached_response(prompt)
                if cached:
                    logger.info("Resposta encontrada no cache")
                    if sender_phone:
                        # Atualiza contexto mesmo com resposta do cache
                        await conversation_manager.update_conversation_context(
                            sender_phone, prompt, cached["response"]
                        )
                    return cached

            # Obtém contexto da conversa se tiver sender_phone
            context = []
            if sender_phone:
                context = await conversation_manager.get_conversation_context(sender_phone)
                if context:
                    # Adiciona contexto ao prompt
                    formatted_context = "\n".join([
                        f"{'Usuário' if msg['role'] == 'user' else 'Assistente'}: {msg['content']}"
                        for msg in context[-5:]  # Usa últimas 5 mensagens
                    ])
                    prompt = f"Contexto anterior:\n{formatted_context}\n\nNova mensagem: {prompt}"

            # Adiciona prompt de personalidade se tiver persona definida
            personality_prompt = PersonaConfig.get_persona_prompt(self.current_persona)
            if personality_prompt:
                prompt = f"{personality_prompt}\n\n{prompt}"

            # Chama o modelo com fallback
            response = await self._try_model_with_fallback(model, prompt, **kwargs)
            
            # Se geração de áudio foi solicitada
            if generate_audio and response.get("success", True):
                try:
                    voice = kwargs.get("voice", PersonaConfig.get_voice(self.current_persona))
                    audio_result = await audio_service.text_to_speech(
                        text=response["text"],
                        voice=voice
                    )
                    if audio_result.get("success"):
                        response["audio_url"] = audio_result.get("public_url")
                        response["audio_path"] = audio_result.get("file_path")
                except Exception as e:
                    logger.error(f"Erro ao gerar áudio: {str(e)}")
                    response["audio_error"] = str(e)

            # Atualiza cache e contexto
            if response.get("success", True) and use_cache:
                await cache_manager.cache_response(prompt, response)
                
            if sender_phone and response.get("success", True):
                await conversation_manager.update_conversation_context(
                    sender_phone, prompt, response["text"]
                )

            return response

        except Exception as e:
            logger.error(f"Erro no roteamento: {str(e)}")
            return {
                "text": "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
                "success": False,
                "error": str(e)
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