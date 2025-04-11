from typing import Dict, Any, Optional
from datetime import datetime
from .supabase import supabase
from api.utils.logger import logger

class HistoryManager:
    def __init__(self):
        self.table_name = "message_history"
    
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
        Salva uma mensagem no histórico
        
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
            data = {
                "sender_phone": sender_phone,
                "message_type": message_type,
                "content": content,
                "model_used": model_used,
                "response": response,
                "success": success,
                "error_message": error_message,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table(self.table_name).insert(data).execute()
            
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
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
                
            if not result.data:
                return {"messages": [], "total": 0}
                
            return {
                "messages": result.data,
                "total": len(result.data)
            }
            
        except Exception as e:
            logger.error(f"Erro ao recuperar histórico: {str(e)}")
            return {"messages": [], "total": 0}

# Instância global do gerenciador de histórico
history_manager = HistoryManager() 