from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timedelta, timezone
from .supabase import supabase
from .logger import logger, log_memory_operation, log_memory_stats
import json

class ConversationManager:
    def __init__(self):
        self.table_name = "conversation_memory"
        self.max_messages = 50  # Limite de mensagens
        self.inactive_hours = 24  # Tempo para inatividade
        self.context_window = 10  # Número de mensagens mantidas ao mudar de assunto
        
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
        topic_change_indicators = [
            "mudando de assunto",
            "outro assunto",
            "falando de outra coisa",
            "voltando ao assunto",
            "sobre outro tema",
            "agora quero falar",
            "vamos falar de",
            "vamos falar sobre"
        ]
        
        return any(indicator.lower() in new_message.lower() for indicator in topic_change_indicators)

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
            
            # Detecta mudança de assunto
            if role == "user" and self._detect_topic_change(messages, content):
                # Registra a mudança de tópico
                topic_changes = conversation_memory.get("topic_changes", [])
                topic_changes.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message_index": len(messages)
                })
                
                # Mantém apenas as últimas X mensagens do contexto anterior
                if len(messages) > self.context_window:
                    messages = messages[-self.context_window:]
                
                log_memory_operation("topic_change", sender_phone, {
                    "old_size": len(messages),
                    "new_size": self.context_window
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
                    "current_topic": conversation_memory.get("current_topic"),
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
            
            # Se houver mudanças de tópico, usa apenas as mensagens desde a última mudança
            if topic_changes:
                last_topic_change = topic_changes[-1]
                last_change_index = last_topic_change["message_index"]
                messages = messages[last_change_index:]
                logger.info(f"Usando mensagens após mudança de tópico (índice {last_change_index})")
            
            formatted_messages = []
            for msg in messages:
                prefix = "Usuário" if msg["role"] == "user" else "Assistente"
                formatted_messages.append(f"{prefix}: {msg['content']}")
            
            # Controle de tokens
            context = "\n".join(formatted_messages)
            if len(context.split()) > max_tokens:
                words = context.split()
                context = " ".join(words[-max_tokens:])
                logger.info(f"Contexto truncado para {max_tokens} tokens")
            
            logger.info(f"Contexto formatado com {len(formatted_messages)} mensagens")
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