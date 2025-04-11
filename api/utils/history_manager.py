from typing import Dict, Any, Optional
from datetime import datetime
from .supabase import supabase
from api.utils.logger import logger

class HistoryManager:
    def __init__(self):
        self.table_name = "conversation_memory"
    
    async def save_message(
        self,
        sender_phone: str,
        message_type: str,
        content: str,
        model_used: Optional[str] = None,
        response: Optional[str] = None,
        success: bool = False,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Salva uma mensagem no histórico usando a tabela conversation_memory
        
        Args:
            sender_phone: Número do remetente
            message_type: Tipo da mensagem (user/assistant)
            content: Conteúdo da mensagem
            model_used: Modelo usado (se aplicável)
            response: Resposta gerada (se aplicável)
            success: Se a operação foi bem sucedida
            error_message: Mensagem de erro (se houver)
            
        Returns:
            Dict com os dados salvos
        """
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
                        "messages": [{
                            "role": message_type,
                            "content": content,
                            "timestamp": datetime.utcnow().isoformat(),
                            "model_used": model_used,
                            "success": success,
                            "error_message": error_message
                        }]
                    }
                }
                result = supabase.table(self.table_name).insert(data).execute()
                logger.info(f"Novo registro de memória criado para {sender_phone}")
            else:
                # Atualiza registro existente
                memory = result.data[0]
                messages = memory["conversation_memory"]["messages"]
                
                # Adiciona nova mensagem
                messages.append({
                    "role": message_type,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": model_used,
                    "success": success,
                    "error_message": error_message
                })
                
                # Atualiza o registro
                data = {
                    "conversation_memory": {"messages": messages},
                    "last_update": datetime.utcnow().isoformat()
                }
                
                result = supabase.table(self.table_name)\
                    .update(data)\
                    .eq("sender_phone", sender_phone)\
                    .execute()
            
            if not result.data:
                logger.error(f"Falha ao salvar mensagem no histórico para {sender_phone}")
                return None
                
            logger.info(f"Mensagem salva no histórico para {sender_phone}")
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Erro ao salvar mensagem no histórico: {str(e)}")
            logger.exception("Stacktrace completo:")
            return None
    
    async def get_message_history(
        self,
        sender_phone: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Recupera o histórico de mensagens de um número
        
        Args:
            sender_phone: Número do remetente
            limit: Limite de mensagens
            offset: Offset para paginação
            
        Returns:
            Dict com o histórico de mensagens
        """
        try:
            result = supabase.table(self.table_name)\
                .select("*")\
                .eq("sender_phone", sender_phone)\
                .execute()
                
            if not result.data:
                return {"messages": [], "total": 0}
                
            memory = result.data[0]
            messages = memory["conversation_memory"]["messages"]
            
            # Aplica paginação
            total = len(messages)
            paginated_messages = messages[offset:offset + limit]
            
            return {
                "messages": paginated_messages,
                "total": total
            }
            
        except Exception as e:
            logger.error(f"Erro ao recuperar histórico: {str(e)}")
            return {"messages": [], "total": 0}

# Instância global do gerenciador de histórico
history_manager = HistoryManager() 