from typing import Dict, Any, List
import json
from datetime import datetime
from loguru import logger
from ..utils.database import SupabaseManager


class MessageQueue:
    def __init__(self):
        self.db = SupabaseManager()
        logger.info("📬 Message Queue inicializada com Supabase")

    async def add_message(
        self, sender: str, prompt: str, response: Dict[str, Any]
    ) -> None:
        """
        Adiciona uma mensagem à fila do sender no Supabase
        """
        try:
            query = """
            INSERT INTO message_queue (sender, prompt, response, status, created_at)
            VALUES (:sender, :prompt, :response, 'pending', NOW())
            """

            await self.db.execute(
                query,
                {
                    "sender": sender,
                    "prompt": prompt,
                    "response": json.dumps(response),
                },
            )

            logger.info(f"📨 Mensagem adicionada à fila para sender: {sender}")

        except Exception as e:
            logger.error(f"❌ Erro ao adicionar mensagem à fila: {str(e)}")

    async def get_messages(self, sender: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna as últimas mensagens do sender do Supabase
        """
        try:
            query = """
            SELECT prompt, response, created_at, status
            FROM message_queue
            WHERE sender = :sender
            ORDER BY created_at DESC
            LIMIT :limit
            """

            result = await self.db.fetch_all(query, {"sender": sender, "limit": limit})

            if result:
                logger.info(
                    f"📋 Retornando {len(result)} mensagens para sender: {sender}"
                )
                return [dict(row) for row in result]

            logger.info(f"ℹ️ Nenhuma mensagem encontrada para sender: {sender}")
            return []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar mensagens: {str(e)}")
            return []

    async def mark_processed(self, message_id: int) -> None:
        """
        Marca uma mensagem como processada
        """
        try:
            query = """
            UPDATE message_queue
            SET status = 'processed',
                processed_at = NOW()
            WHERE id = :message_id
            """

            await self.db.execute(query, {"message_id": message_id})
            logger.info(f"✅ Mensagem {message_id} marcada como processada")

        except Exception as e:
            logger.error(f"❌ Erro ao marcar mensagem como processada: {str(e)}")

    async def get_pending_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retorna mensagens pendentes ordenadas por prioridade
        """
        try:
            query = """
            SELECT id, sender, prompt, response, priority
            FROM message_queue
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT :limit
            """

            result = await self.db.fetch_all(query, {"limit": limit})

            if result:
                logger.info(f"📥 Retornando {len(result)} mensagens pendentes")
                return [dict(row) for row in result]

            return []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar mensagens pendentes: {str(e)}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da fila
        """
        try:
            query = """
            SELECT 
                COUNT(*) as total_messages,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_messages,
                COUNT(*) FILTER (WHERE status = 'processed') as processed_messages,
                COUNT(DISTINCT sender) as total_senders
            FROM message_queue
            """

            result = await self.db.fetch_one(query)

            if result:
                stats = dict(result)
                logger.info(f"📊 Estatísticas da fila: {stats}")
                return stats

            return {
                "total_messages": 0,
                "pending_messages": 0,
                "processed_messages": 0,
                "total_senders": 0,
            }

        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {str(e)}")
            return {
                "total_messages": 0,
                "pending_messages": 0,
                "processed_messages": 0,
                "total_senders": 0,
            }
