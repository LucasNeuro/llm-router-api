from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timedelta, timezone
from .supabase import supabase
from .logger import logger, log_memory_operation, log_memory_stats
import json
import re
from ..llm_router.mistral import call_mistral

class ConversationManager:
    def __init__(self):
        self.table_name = "conversation_memory"
        self.max_messages = 50  # Limite de mensagens
        self.inactive_hours = 24  # Tempo para inatividade
        self.context_window = 10  # Número de mensagens mantidas ao mudar de assunto
        self.use_ai_topic_detection = True  # Usa IA para detecção de tópicos
        
    async def _get_memory_status(self, sender_phone: str) -> bool:
        """Verifica se a memória está ativa para o número"""
        try:
            result = supabase.table(self.table_name)\
                .select("is_active")\
                .eq("sender_phone", sender_phone)\
                .execute()
                
            if not result.data:
                # Se não existir, cria com memória ativa
                data = {
                    "sender_phone": sender_phone,
                    "conversation_memory": {"messages": []},
                    "is_active": True,
                    "last_update": datetime.now(timezone.utc).isoformat()
                }
                supabase.table(self.table_name).insert(data).execute()
                return True
                
            return result.data[0].get("is_active", True)
            
        except Exception as e:
            logger.error(f"Erro ao verificar status da memória: {str(e)}")
            return True  # Por padrão, mantém ativa
    
    async def toggle_memory(self, sender_phone: str, active: bool) -> None:
        """Ativa ou desativa a memória para um número"""
        try:
            data = {
                "is_active": active,
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            if active:
                # Se ativando, limpa a memória
                data["conversation_memory"] = {
                    "messages": [],
                    "current_topic": None,
                    "topic_changes": []
                }
            
            result = supabase.table(self.table_name)\
                .update(data)\
                .eq("sender_phone", sender_phone)\
                .execute()
                
            logger.info(f"Memória {'ativada' if active else 'desativada'} para {sender_phone}")
            
        except Exception as e:
            logger.error(f"Erro ao alterar status da memória: {str(e)}")
            
    async def clear_memory(self, sender_phone: str) -> None:
        """Limpa manualmente a memória de um número"""
        try:
            data = {
                "conversation_memory": {
                    "messages": [],
                    "current_topic": None,
                    "topic_changes": []
                },
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table(self.table_name)\
                .update(data)\
                .eq("sender_phone", sender_phone)\
                .execute()
                
            logger.info(f"Memória limpa manualmente para {sender_phone}")
            
        except Exception as e:
            logger.error(f"Erro ao limpar memória: {str(e)}")

    async def _get_or_create_memory(self, sender_phone: str) -> Dict[str, Any]:
        """Recupera ou cria o registro de memória para o número"""
        try:
            # Verifica se a memória está ativa
            is_active = await self._get_memory_status(sender_phone)
            if not is_active:
                log_memory_operation("status_check", sender_phone, {"active": False})
                return {
                    "sender_phone": sender_phone,
                    "conversation_memory": {
                        "messages": [],
                        "current_topic": None,
                        "topic_changes": []
                    },
                    "last_update": datetime.now(timezone.utc).isoformat(),
                    "is_active": False
                }

            # Tenta recuperar o registro existente
            result = supabase.table(self.table_name)\
                .select("*")\
                .eq("sender_phone", sender_phone)\
                .execute()

            current_time = datetime.now(timezone.utc)
            
            if not result.data:
                # Cria novo registro se não existir
                data = {
                    "sender_phone": sender_phone,
                    "conversation_memory": {
                        "messages": [],
                        "current_topic": None,
                        "topic_changes": []
                    },
                    "last_update": current_time.isoformat(),
                    "is_active": True
                }
                result = supabase.table(self.table_name).insert(data).execute()
                log_memory_operation("created", sender_phone)
                return result.data[0]
            
            # Verifica se a conversa está inativa por tempo
            memory_data = result.data[0]
            last_update = datetime.fromisoformat(memory_data.get("last_update"))
            if not last_update.tzinfo:
                last_update = last_update.replace(tzinfo=timezone.utc)
                
            if current_time - last_update > timedelta(hours=self.inactive_hours):
                # Limpa a memória se estiver inativa por mais de 24 horas
                data = {
                    "conversation_memory": {
                        "messages": [],
                        "current_topic": None,
                        "topic_changes": []
                    },
                    "last_update": current_time.isoformat()
                }
                result = supabase.table(self.table_name)\
                    .update(data)\
                    .eq("sender_phone", sender_phone)\
                    .execute()
                logger.info(f"Memória limpa por inatividade para {sender_phone}")
                return result.data[0]
            
            # Verifica limite de mensagens
            messages = memory_data["conversation_memory"]["messages"]
            if len(messages) > self.max_messages:
                messages = messages[-self.max_messages:]
                data = {
                    "conversation_memory": {
                        "messages": messages,
                        "current_topic": memory_data["conversation_memory"].get("current_topic"),
                        "topic_changes": memory_data["conversation_memory"].get("topic_changes", [])
                    },
                    "last_update": current_time.isoformat()
                }
                result = supabase.table(self.table_name)\
                    .update(data)\
                    .eq("sender_phone", sender_phone)\
                    .execute()
                logger.info(f"Memória truncada para {sender_phone} (limite de {self.max_messages} mensagens)")
                return result.data[0]
            
            return memory_data

        except Exception as e:
            logger.error(f"Erro ao recuperar/criar memória: {str(e)}")
            logger.exception("Stacktrace completo:")
            raise

    def _detect_topic_change(self, current_messages: List[Dict], new_message: str) -> bool:
        """Detecta mudança de assunto baseado em palavras-chave"""
        # Lista de frases que explicitamente indicam mudança de assunto
        topic_change_indicators = [
            "mudando de assunto",
            "outro assunto",
            "falando de outra coisa",
            "voltando ao assunto",
            "sobre outro tema"
        ]
        
        # Frases que exigem um tema específico depois para ser considerada mudança
        # "vamos falar de X" só é mudança se X for substantivo/tema
        conditional_indicators = [
            "vamos falar de",
            "vamos falar sobre",
            "agora quero falar",
            "agora vamos falar"
        ]
        
        # Checa indicadores diretos
        if any(indicator.lower() in new_message.lower() for indicator in topic_change_indicators):
            return True
            
        # Para indicadores condicionais, verifica se há realmente um novo tema
        for indicator in conditional_indicators:
            if indicator.lower() in new_message.lower():
                # Extrai o que vem depois do indicador
                parts = new_message.lower().split(indicator.lower())
                if len(parts) > 1:
                    # Verifica se o que vem depois tem pelo menos 4 caracteres
                    # e não é apenas uma pergunta
                    potential_topic = parts[1].strip()
                    if (len(potential_topic) > 4 and 
                        not potential_topic.startswith("?") and
                        not potential_topic.endswith("?")):
                        return True
        
        return False

    async def _detect_topic_change_with_ai(self, current_messages: List[Dict], new_message: str) -> Dict[str, Any]:
        """Usa IA (Mistral) para detectar mudanças de tópico e extrair o novo tema"""
        try:
            # Se não tiver mensagens anteriores, não é mudança de tópico
            if not current_messages:
                return {
                    "is_topic_change": False,
                    "new_topic": self._extract_topic(new_message),
                    "confidence": 0
                }
            
            # Pega as últimas 3 mensagens para contexto (ou menos, se não houver tantas)
            context_messages = current_messages[-3:] if len(current_messages) >= 3 else current_messages
            context = "\n".join([f"{'Usuário' if msg['role'] == 'user' else 'Assistente'}: {msg['content']}" for msg in context_messages])
            
            # Monta o prompt para o Mistral
            prompt = f"""Analise a conversa abaixo e determine se a última mensagem do usuário representa uma mudança clara de assunto.
            
Conversa anterior:
{context}

Nova mensagem do usuário:
{new_message}

Responda apenas em formato JSON como no exemplo:
{{
  "is_topic_change": true|false,
  "new_topic": "nome do novo tópico se houver mudança, ou do tópico atual se não houver mudança",
  "previous_topic": "nome do tópico anterior, se detectado",
  "confidence": 0.9 // valor entre 0 e 1 indicando sua confiança nesta classificação
}}

Exemplos para guiar sua classificação:
1. Uma mudança de "política" para "esportes" seria uma mudança clara (is_topic_change: true)
2. Perguntas seguintes sobre o mesmo tema não são mudanças (is_topic_change: false)
3. Retomar um tópico mencionado anteriormente conta como mudança (is_topic_change: true)
4. Perguntas não relacionadas ao contexto anterior são mudanças (is_topic_change: true)
5. Perguntas sobre a conversa em si não são mudanças (is_topic_change: false)

Responda apenas com o JSON:"""

            # Chama o Mistral para análise
            result = await call_mistral(prompt)
            
            try:
                # Tenta extrair o JSON da resposta
                if isinstance(result, str):
                    # Remove possíveis textos antes ou depois do JSON
                    json_str = result.strip()
                    # Se houver texto explicativo antes ou depois do JSON, tenta extrair só o JSON
                    if json_str.find('{') >= 0 and json_str.rfind('}') > json_str.find('{'):
                        json_str = json_str[json_str.find('{'):json_str.rfind('}')+1]
                    
                    analysis = json.loads(json_str)
                else:
                    # Se já for um dicionário
                    analysis = result
                
                # Garante que todos os campos necessários existem
                if "is_topic_change" not in analysis:
                    analysis["is_topic_change"] = False
                if "new_topic" not in analysis or not analysis["new_topic"]:
                    analysis["new_topic"] = self._extract_topic(new_message)
                if "confidence" not in analysis:
                    analysis["confidence"] = 0.5
                    
                log_memory_operation("ai_topic_detection", "system", {
                    "is_change": analysis["is_topic_change"],
                    "new_topic": analysis["new_topic"],
                    "confidence": analysis["confidence"]
                })
                
                return analysis
                
            except json.JSONDecodeError:
                logger.error(f"Erro ao decodificar JSON da resposta do Mistral: {result}")
                # Fallback para detecção baseada em regras
                return {
                    "is_topic_change": self._detect_topic_change(current_messages, new_message),
                    "new_topic": self._extract_topic(new_message),
                    "confidence": 0.3
                }
                
        except Exception as e:
            logger.error(f"Erro na detecção de tópico com IA: {str(e)}")
            logger.exception("Stacktrace detalhado:")
            # Fallback para detecção baseada em regras
            return {
                "is_topic_change": self._detect_topic_change(current_messages, new_message),
                "new_topic": self._extract_topic(new_message),
                "confidence": 0.3
            }

    async def add_message(
        self,
        sender_phone: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        save_to_db: bool = True
    ) -> None:
        """Adiciona uma mensagem à memória"""
        if not save_to_db:
            return

        try:
            # Verifica se a memória está ativa
            is_active = await self._get_memory_status(sender_phone)
            if not is_active:
                log_memory_operation("skipped", sender_phone, {"reason": "memory_inactive"})
                return

            # Recupera ou cria o registro de memória
            memory = await self._get_or_create_memory(sender_phone)
            conversation_memory = memory["conversation_memory"]
            messages = conversation_memory.get("messages", [])
            
            # Detecta mudança de assunto apenas em mensagens do usuário
            is_topic_change = False
            new_topic = None
            
            if role == "user":
                # Usa IA para detecção de tópicos ou fallback para o método baseado em regras
                if self.use_ai_topic_detection:
                    analysis = await self._detect_topic_change_with_ai(messages, content)
                    is_topic_change = analysis["is_topic_change"]
                    new_topic = analysis["new_topic"]
                else:
                    is_topic_change = self._detect_topic_change(messages, content)
                    new_topic = self._extract_topic(content)
                
                # Se for mudança de tópico
                if is_topic_change:
                    # Registra a mudança de tópico
                    topic_changes = conversation_memory.get("topic_changes", [])
                    previous_topic = conversation_memory.get("current_topic")
                    
                    # Registra a mudança
                    topic_change = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "message_index": len(messages),
                        "previous_topic": previous_topic,
                        "new_topic": new_topic
                    }
                    
                    topic_changes.append(topic_change)
                    conversation_memory["current_topic"] = new_topic
                    
                    log_memory_operation("topic_change", sender_phone, {
                        "previous_topic": previous_topic,
                        "new_topic": new_topic,
                        "detection_method": "ai" if self.use_ai_topic_detection else "rules"
                    })
            
            # Prepara a nova mensagem
            new_message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model_used": model_used
            }
            
            # Adiciona a nova mensagem
            messages.append(new_message)
            
            # Se exceder o limite, remove as mensagens mais antigas
            if len(messages) > self.max_messages:
                messages = messages[-self.max_messages:]
                log_memory_operation("truncated", sender_phone, {"new_size": len(messages)})
            
            # Atualiza o registro no Supabase
            data = {
                "conversation_memory": {
                    "messages": messages,
                    "current_topic": conversation_memory.get("current_topic", new_topic),
                    "topic_changes": conversation_memory.get("topic_changes", [])
                },
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table(self.table_name)\
                .update(data)\
                .eq("sender_phone", sender_phone)\
                .execute()
            
            log_memory_stats(sender_phone, len(messages), True)

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem: {str(e)}")
            logger.exception("Stacktrace completo:")

    def _extract_topic(self, message: str) -> Optional[str]:
        """Extrai o tópico de uma mensagem"""
        # Lista de frases indicadoras para extração de tópico
        topic_indicators = [
            "vamos falar de",
            "vamos falar sobre",
            "agora quero falar sobre",
            "mudando para",
            "sobre o tema"
        ]
        
        message_lower = message.lower()
        
        # Tenta extrair o tópico de frases como "vamos falar de X"
        for indicator in topic_indicators:
            if indicator in message_lower:
                parts = message_lower.split(indicator)
                if len(parts) > 1:
                    # Extrai o tópico após o indicador
                    topic = parts[1].strip()
                    # Remove pontuação no final
                    topic = re.sub(r'[?.!,:;].*$', '', topic)
                    # Limita o tamanho do tópico
                    if len(topic) > 30:
                        topic = topic[:30]
                    if len(topic) > 0:
                        return topic
        
        # Se não encontrou um tópico explícito, tenta extrair palavras-chave
        # Implementação simples - em uma versão mais avançada, poderíamos
        # usar NLP para extrair entidades ou tópicos principais
        
        # Remover stopwords simples e pegar as primeiras palavras
        stopwords = ["a", "o", "e", "de", "da", "do", "em", "para", "com", "por", "um", "uma"]
        words = message_lower.split()
        keywords = [word for word in words if len(word) > 3 and word not in stopwords]
        
        if keywords:
            # Usa as primeiras palavras-chave como tópico
            topic = " ".join(keywords[:3])
            if len(topic) > 30:
                topic = topic[:30]
            return topic
        
        return None

    async def format_conversation_for_llm(self, sender_phone: str, max_tokens: int = 4000) -> str:
        """Formata a conversa para o LLM com contexto inteligente"""
        try:
            # Verifica se a memória está ativa
            is_active = await self._get_memory_status(sender_phone)
            if not is_active:
                logger.info(f"Memória desativada para {sender_phone}, retornando contexto vazio")
                return ""

            # Recupera o registro de memória
            memory = await self._get_or_create_memory(sender_phone)
            messages = memory["conversation_memory"]["messages"]
            topic_changes = memory["conversation_memory"].get("topic_changes", [])
            
            # Prepara lista para armazenar mensagens que serão enviadas para o LLM
            formatted_messages = []
            
            # Se houver mudanças de tópico
            if topic_changes and len(topic_changes) > 0:
                # Pega a última mudança de tópico
                last_topic_change = topic_changes[-1]
                last_change_index = last_topic_change.get("message_index", 0)
                
                # Cria um resumo das conversas anteriores
                previous_messages = messages[:last_change_index] if last_change_index > 0 else []
                if previous_messages:
                    # Extrai as perguntas importantes feitas anteriormente
                    important_questions = []
                    important_facts = []
                    
                    for i, msg in enumerate(previous_messages):
                        if msg["role"] == "user" and len(msg["content"]) > 5 and "?" in msg["content"]:
                            question = msg["content"]
                            # Se houver uma resposta, inclui
                            if i+1 < len(previous_messages) and previous_messages[i+1]["role"] == "assistant":
                                answer = previous_messages[i+1]["content"]
                                # Limita o tamanho para não consumir muito contexto
                                if len(answer) > 100:
                                    answer = answer[:100] + "..."
                                important_facts.append(f"Pergunta: {question}\nResposta: {answer}")
                            else:
                                important_questions.append(question)
                    
                    # Adiciona um resumo das conversas anteriores
                    if important_facts or important_questions:
                        summary = "### Resumo da conversa anterior:\n"
                        
                        if important_facts:
                            summary += "\nFatos importantes discutidos:\n"
                            for fact in important_facts[:3]:  # Limita a 3 fatos
                                summary += f"- {fact}\n"
                                
                        if important_questions:
                            summary += "\nPerguntas anteriores:\n"
                            for question in important_questions[:3]:  # Limita a 3 perguntas
                                summary += f"- {question}\n"
                        
                        formatted_messages.append(summary)
                        
                        # Adiciona uma linha separadora
                        formatted_messages.append("### Conversa atual:")
                
                # Pega as mensagens após a última mudança de tópico
                current_context = messages[last_change_index:]
            else:
                current_context = messages
            
            # Adiciona as mensagens do contexto atual
            for msg in current_context:
                prefix = "Usuário" if msg["role"] == "user" else "Assistente"
                formatted_messages.append(f"{prefix}: {msg['content']}")
            
            # Junta tudo em um único texto
            context = "\n".join(formatted_messages)
            
            # Controle de tokens
            if len(context.split()) > max_tokens:
                words = context.split()
                context = " ".join(words[-max_tokens:])
                logger.info(f"Contexto truncado para {max_tokens} tokens")
            
            return context
            
        except Exception as e:
            logger.error(f"Erro ao formatar conversa: {str(e)}")
            logger.exception("Stacktrace completo:")
            return ""

    async def cleanup_inactive_sessions(self) -> None:
        """Limpa sessões inativas e registros antigos"""
        try:
            current_time = datetime.now(timezone.utc)
            time_limit = current_time - timedelta(hours=self.inactive_hours)
            
            # Limpa memória de conversas inativas
            data = {
                "conversation_memory": {
                    "messages": [],
                    "current_topic": None,
                    "topic_changes": []
                },
                "last_update": current_time.isoformat()
            }
            
            supabase.table(self.table_name)\
                .update(data)\
                .lt("last_update", time_limit.isoformat())\
                .execute()
            
            logger.info(f"Limpeza de sessões inativas concluída (mais de {self.inactive_hours} horas)")
        
        except Exception as e:
            logger.error(f"Erro ao limpar sessões inativas: {str(e)}")
            logger.exception("Stacktrace completo:")

# Instância global do gerenciador de conversas
conversation_manager = ConversationManager()