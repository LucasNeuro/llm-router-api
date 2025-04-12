from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timedelta
from .supabase import supabase
from api.utils.logger import logger
import json

class ConversationManager:
    def __init__(self):
        self.table_name = "conversation_memory"
        self.max_messages = 100  # Limite de mensagens por número
    
    async def _get_or_create_memory(self, sender_phone: str) -> Dict[str, Any]:
        """Recupera ou cria o registro de memória para o número"""
        try:
            # Tenta recuperar o registro existente
            result = supabase.table(self.table_name)\
                .select("*")\
                .eq("sender_phone", sender_phone)\
                .execute()

            if not result.data:
                # Cria novo registro se não existir
                data = {
                    "sender_phone": sender_phone,
                    "conversation_memory": {
                        "messages": []
                    }
                }
                result = supabase.table(self.table_name).insert(data).execute()
                logger.info(f"Novo registro de memória criado para {sender_phone}")
                return result.data[0]
            
            return result.data[0]

        except Exception as e:
            logger.error(f"Erro ao recuperar/criar memória: {str(e)}")
            raise

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
            # Recupera ou cria o registro de memória
            memory = await self._get_or_create_memory(sender_phone)
            
            # Prepara a nova mensagem
            new_message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": model_used
            }

            # Recupera as mensagens existentes
            messages = memory["conversation_memory"]["messages"]
            
            # Adiciona a nova mensagem
            messages.append(new_message)
            
            # Se exceder o limite, remove as mensagens mais antigas
            if len(messages) > self.max_messages:
                messages = messages[-self.max_messages:]
            
            # Atualiza o registro no Supabase
            data = {
                "conversation_memory": {"messages": messages},
                "last_update": datetime.utcnow().isoformat()
            }
            
            supabase.table(self.table_name)\
                .update(data)\
                .eq("sender_phone", sender_phone)\
                .execute()
            
            logger.info(f"Memória atualizada para {sender_phone}: {len(messages)} mensagens")

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem: {str(e)}")
            logger.exception("Stacktrace completo:")

    async def format_conversation_for_llm(self, sender_phone: str, max_tokens: int = 4000) -> str:
        """Formata a conversa para o LLM"""
        try:
            # Recupera o registro de memória
            memory = await self._get_or_create_memory(sender_phone)
            messages = memory["conversation_memory"]["messages"]
            
            formatted_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    formatted_messages.append(f"Usuário: {msg['content']}")
                else:
                    formatted_messages.append(f"Assistente: {msg['content']}\n")
            
            # Controle de tokens
            context = "\n".join(formatted_messages)
            if len(context.split()) > max_tokens:
                words = context.split()
                context = " ".join(words[-max_tokens:])
            
            return context

        except Exception as e:
            logger.error(f"Erro ao formatar conversa: {str(e)}")
            return ""

    async def cleanup_old_memories(self, days: int = 30) -> None:
        """Remove memórias antigas"""
        try:
            time_limit = datetime.utcnow() - timedelta(days=days)
            
            supabase.table(self.table_name)\
                .delete()\
                .lt("last_update", time_limit.isoformat())\
                .execute()
            
            logger.info(f"Limpeza de memórias antigas concluída (mais de {days} dias)")
        
        except Exception as e:
            logger.error(f"Erro ao limpar memórias antigas: {str(e)}")

# Instância global do gerenciador de conversas
conversation_manager = ConversationManager()