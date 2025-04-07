from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger
import os
import json


class SupabaseManager:
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        )
        self.max_context_messages = 50  # Limite máximo de mensagens por contexto
        self.context_ttl = 24  # TTL em horas
        logger.info("Supabase manager initialized")

    async def execute(self, query: str, params: Dict[str, Any] = None):
        """Executa uma query no Supabase"""
        try:
            # Como o Supabase não tem execute direto, vamos usar o rpc
            result = self.supabase.rpc(
                "exec_sql", 
                {"sql": query, "params": json.dumps(params) if params else "{}"}
            ).execute()
            return result.data
        except Exception as e:
            logger.error(f"Erro ao executar query: {str(e)}")
            raise

    async def fetch_one(self, query: str, params: Dict[str, Any] = None):
        """Busca um único resultado"""
        try:
            result = await self.execute(query, params)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Erro ao buscar resultado: {str(e)}")
            raise

    async def fetch_all(self, query: str, params: Dict[str, Any] = None):
        """Busca múltiplos resultados"""
        try:
            return await self.execute(query, params)
        except Exception as e:
            logger.error(f"Erro ao buscar resultados: {str(e)}")
            raise

    async def get_from_cache(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Busca do cache"""
        try:
            result = self.supabase.table("response_cache").select("*") \
                .eq("prompt", prompt) \
                .gt("expires_at", datetime.utcnow().isoformat()) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()

            if result.data:
                return result.data[0]["response"]
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar do cache: {str(e)}")
            return None

    async def save_to_cache(self, prompt: str, response: Dict[str, Any], model: str):
        """Salva no cache"""
        try:
            if not prompt or not response or not model:
                logger.warning("Dados inválidos para cache")
                return

            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Formata a resposta no padrão JSONB
            formatted_response = {
                "text": response.get("text", ""),
                "success": response.get("success", True),
                "cost_analysis": response.get("cost_analysis", {}),
                "model": response.get("model", ""),
                "confidence": response.get("confidence", 0.0),
                "model_scores": response.get("model_scores", {}),
                "indicators": response.get("indicators", {})
            }

            data = {
                "prompt": prompt,
                "response": formatted_response,
                "model": model,
                "expires_at": expires_at.isoformat(),
                "usage_count": 1
            }

            # Usa upsert para atualizar se já existe
            result = self.supabase.table("response_cache") \
                .upsert(data, on_conflict="prompt") \
                .execute()
                
            logger.info("Cache atualizado com sucesso")
            return result

        except Exception as e:
            logger.error(f"Erro ao salvar cache: {str(e)}")

    async def add_to_queue(
        self,
        sender: str,
        prompt: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Adiciona mensagem à fila de processamento
        Args:
            sender: ID do remetente
            prompt: Texto do prompt (opcional)
            response: Resposta do modelo (opcional)
        Returns:
            ID da mensagem na fila
        """
        try:
            # Prepara message_queue
            message_queue = {}
            if prompt:
                message_queue["prompt"] = prompt
            if response:
                message_queue["response"] = response

            data = {
                "sender": sender,
                "status": "pending" if not response else "completed",
                "created_at": datetime.utcnow().isoformat(),
                "message_queue": message_queue
            }
            
            if response:
                data["processed_at"] = datetime.utcnow().isoformat()
            
            # Usa o formato correto do Supabase
            result = self.supabase.table("message_queue").insert(data).execute()
            msg_id = result.data[0]["id"]
            logger.info(f"Mensagem {msg_id} adicionada à fila para {sender}")
            return msg_id

        except Exception as e:
            logger.error(f"Erro ao adicionar à fila: {str(e)}")
            raise

    async def get_pending_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna mensagens pendentes ordenadas por data de criação"""
        try:
            result = self.supabase.table("message_queue") \
                .select("id, sender, message_queue, status, created_at") \
                .eq("status", "pending") \
                .order("created_at", desc=False) \
                .limit(limit) \
                .execute()

            if result.data:
                logger.info(f"📥 Retornando {len(result.data)} mensagens pendentes")
                return result.data

            return []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar mensagens pendentes: {str(e)}")
            return []

    async def update_queue_status(
        self, 
        msg_id: str, 
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Atualiza status da mensagem na fila
        Args:
            msg_id: ID da mensagem
            status: Novo status
            metadata: Dados adicionais para atualizar
        """
        try:
            data = {
                "status": status,
                "processed_at": datetime.utcnow().isoformat() if status == "completed" else None
            }
            
            if metadata:
                data["message_queue"] = metadata
            
            self.supabase.table("message_queue") \
                .update(data) \
                .eq("id", msg_id) \
                .execute()
                
            logger.info(f"Status da mensagem {msg_id} atualizado para {status}")

        except Exception as e:
            logger.error(f"Erro ao atualizar status: {str(e)}")
            raise

    async def save_context(
        self, 
        sender: str, 
        new_messages: List[Dict[str, Any]], 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Salva ou atualiza o contexto da conversa
        Args:
            sender: ID do remetente
            new_messages: Lista de novas mensagens para adicionar
            metadata: Dados adicionais como modelo usado, scores, etc
        """
        try:
            # Busca contexto existente
            existing = await self.get_context(sender)
            messages = existing.copy() if existing else []
            
            # Adiciona novas mensagens
            for msg in new_messages:
                if not msg.get("timestamp"):
                    msg["timestamp"] = datetime.utcnow().isoformat()
                messages.append(msg)
            
            # Mantém apenas as últimas max_context_messages
            if len(messages) > self.max_context_messages:
                messages = messages[-self.max_context_messages:]
            
            # Prepara dados
            data = {
                "sender": sender,
                "messages": messages,
                "message_count": len(messages),
                "last_interaction": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=self.context_ttl)).isoformat()
            }
            
            # Adiciona metadata se fornecido
            if metadata:
                data["metadata"] = metadata
            
            # Salva no Supabase
            result = self.supabase.table("conversation_context") \
                .upsert(data, on_conflict="sender") \
                .execute()
                
            logger.info(f"Contexto atualizado para {sender} com {len(messages)} mensagens")
            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Erro ao salvar contexto: {str(e)}")
            raise

    async def get_context(self, sender: str) -> List[Dict[str, Any]]:
        """
        Busca o contexto da conversa
        Args:
            sender: ID do remetente
        Returns:
            Lista de mensagens do contexto
        """
        try:
            result = self.supabase.table("conversation_context") \
                .select("messages") \
                .eq("sender", sender) \
                .gt("expires_at", datetime.utcnow().isoformat()) \
                .single() \
                .execute()
            
            if result.data:
                messages = result.data.get("messages", [])
                logger.info(f"Contexto encontrado para {sender}: {len(messages)} mensagens")
                return messages
            
            logger.info(f"Nenhum contexto encontrado para {sender}")
            return []

        except Exception as e:
            logger.error(f"Erro ao buscar contexto: {str(e)}")
            return []

    async def find_similar_response(
        self, 
        sender: str, 
        prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Busca uma resposta similar no contexto do usuário
        Args:
            sender: ID do remetente
            prompt: Texto do prompt
        Returns:
            Resposta similar se encontrada
        """
        try:
            messages = await self.get_context(sender)
            
            # Busca mensagem similar
            for i, msg in enumerate(messages):
                if msg["role"] == "user" and msg["content"].lower() == prompt.lower():
                    # Se encontrar mensagem igual, retorna próxima resposta
                    if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                        logger.info(f"Resposta similar encontrada no contexto de {sender}")
                        return messages[i + 1]
            
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar resposta similar: {str(e)}")
            return None

    async def update_conversation_context(
        self, sender: str, user_message: str, bot_response: str, ttl_hours: int = 24
    ):
        """Atualiza contexto da conversa"""
        try:
            if not sender or not user_message or not bot_response:
                logger.warning("Dados inválidos para contexto")
                return

            # Nova mensagem para adicionar ao contexto
            new_messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": bot_response},
            ]

            # Busca contexto existente
            response = (
                self.supabase.table("conversation_context")
                .select("messages")
                .eq("sender", sender)
                .execute()
            )

            messages = []
            if response.data:
                existing_messages = response.data[0]["messages"]
                if isinstance(existing_messages, str):
                    existing_messages = json.loads(existing_messages)
                messages = existing_messages

            # Adiciona novas mensagens
            messages.extend(new_messages)

            # Mantém apenas as últimas 10 mensagens
            if len(messages) > 10:
                messages = messages[-10:]

            # Atualiza ou insere contexto
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            self.supabase.table("conversation_context").upsert(
                {
                    "sender": sender,
                    "messages": json.dumps(messages),
                    "last_interaction": datetime.utcnow().isoformat(),
                    "expires_at": expires_at.isoformat(),
                }
            ).execute()

            logger.info(f"Contexto atualizado para {sender}")

        except Exception as e:
            logger.error(f"Erro ao atualizar contexto: {str(e)}")

    async def clear_conversation_context(self, sender: str):
        """Limpa contexto da conversa"""
        try:
            if not sender:
                raise ValueError("Sender é obrigatório")

            # Usa índice idx_context_sender
            self.supabase.table("conversation_context").update(
                {"messages": [], "last_interaction": datetime.utcnow().isoformat()}
            ).eq("sender", sender).execute()

            logger.info(f"Contexto limpo para {sender}")

        except Exception as e:
            logger.error(f"Erro ao limpar contexto: {str(e)}")

    async def cleanup_expired(self):
        """Limpa dados expirados de todas as tabelas"""
        try:
            now = datetime.utcnow().isoformat()

            # Limpa cache expirado
            self.supabase.table("response_cache").delete().lte(
                "expires_at", now
            ).execute()

            # Limpa contextos expirados
            self.supabase.table("conversation_context").delete().lte(
                "expires_at", now
            ).execute()

            logger.info("Limpeza de dados expirados concluída")

        except Exception as e:
            logger.error(f"Erro na limpeza de dados: {str(e)}")

    async def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema"""
        try:
            stats = {
                "cache": await self._get_cache_stats(),
                "queue": await self._get_queue_stats(),
                "context": await self._get_context_stats(),
            }
            logger.info(f"Estatísticas coletadas: {json.dumps(stats, indent=2)}")
            return stats
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas: {str(e)}")
            return {}

    async def _get_cache_stats(self) -> Dict[str, int]:
        """Estatísticas do cache"""
        response = (
            self.supabase.table("response_cache")
            .select("count(*)", "sum(usage_count)")
            .execute()
        )
        return {
            "total_entries": response.count,
            "total_hits": response.data[0]["sum"] if response.data else 0,
        }

    async def _get_queue_stats(self) -> Dict[str, int]:
        """Estatísticas da fila"""
        try:
            result = self.supabase.table("message_queue") \
                .select("status, count(*)") \
                .group("status") \
                .execute()
                
            stats = {}
            for row in result.data:
                stats[row["status"]] = row["count"]
                
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas da fila: {str(e)}")
            return {}

    async def _get_context_stats(self) -> Dict[str, int]:
        """Estatísticas dos contextos"""
        response = (
            self.supabase.table("conversation_context")
            .select("count(*)", "count(distinct sender)")
            .execute()
        )
        return {
            "total_contexts": response.count,
            "active_senders": response.data[0]["count"] if response.data else 0,
        }

    async def save_llm_data(
        self,
        request_id: str,
        prompt: str,
        response: str,
        model: str,
        classification: Dict[str, Any],
        cost_analysis: Dict[str, Any],
        sender: Optional[str] = None
    ):
        """Salva dados do LLM Router"""
        try:
            # Formata os dados no padrão JSONB
            data = {
                "request_id": request_id,
                "prompt": prompt,
                "sender": sender,
                "model": model,
                "classification": {
                    "confidence": classification.get("confidence", 0.0),
                    "model_scores": classification.get("model_scores", {}),
                    "indicators": classification.get("indicators", {})
                },
                "response": {
                    "text": response,
                    "success": True,
                    "cost_analysis": cost_analysis
                },
                "created_at": datetime.utcnow().isoformat()
            }

            # Usa o formato correto do Supabase
            result = self.supabase.table("llm_router").insert(data).execute()
            logger.info(f"Dados salvos na tabela llm_router para request_id: {request_id}")
            return result

        except Exception as e:
            logger.error(f"Erro ao salvar dados do LLM Router: {str(e)}")
            raise

    async def clear_expired_contexts(self):
        """Remove contextos expirados"""
        try:
            result = self.supabase.table("conversation_context") \
                .delete() \
                .lt("expires_at", datetime.utcnow().isoformat()) \
                .execute()
                
            if result.data:
                logger.info(f"Removidos {len(result.data)} contextos expirados")

        except Exception as e:
            logger.error(f"Erro ao limpar contextos expirados: {str(e)}")
            raise
