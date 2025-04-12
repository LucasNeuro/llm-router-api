from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime, timedelta
from loguru import logger
from .supabase import supabase
import pytz

class CacheManager:
    """Gerenciador de cache usando Supabase"""
    
    @staticmethod
    def _get_utc_now():
        """Retorna datetime atual com timezone UTC"""
        return datetime.now(pytz.UTC)

    @staticmethod
    def _ensure_cache_table():
        """Garante que a tabela de cache existe"""
        try:
            # Cria a tabela de cache se não existir
            supabase.table('response_cache').select('id').limit(1).execute()
            logger.info("Tabela de cache verificada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao verificar tabela de cache: {str(e)}")
            raise

    @staticmethod
    async def get_cached_response(prompt: str) -> Optional[Dict[str, Any]]:
        """Busca uma resposta no cache"""
        try:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            
            # Busca resposta no cache
            response = supabase.table('response_cache').select('*').eq('prompt_hash', prompt_hash).execute()
            
            if response and response.data:
                cached_data = response.data[0]
                # Verifica se não expirou
                expires_at = datetime.fromisoformat(cached_data['expires_at']).replace(tzinfo=pytz.UTC)
                if expires_at > CacheManager._get_utc_now():
                    logger.info(f"Cache hit para prompt_hash: {prompt_hash}")
                    
                    # Atualiza hit_count e last_accessed
                    current_time = CacheManager._get_utc_now().isoformat()
                    supabase.table('response_cache').update({
                        'hit_count': cached_data['hit_count'] + 1,
                        'last_accessed': current_time
                    }).eq('prompt_hash', prompt_hash).execute()
                    
                    cached_response = json.loads(cached_data['response']) if isinstance(cached_data['response'], str) else cached_data['response']
                    return {
                        "text": cached_response.get("text", ""),
                        "model": cached_data['model'],
                        "success": True,
                        "from_cache": True,
                        "hit_count": cached_data['hit_count'] + 1,
                        "created_at": cached_data['created_at'],
                        "last_accessed": current_time
                    }
            return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar cache: {str(e)}")
            return None

    @staticmethod
    async def cache_response(
        prompt: str, 
        response: Dict[str, Any],
        model: str,
        ttl_hours: int = 24
    ) -> bool:
        """Salva uma resposta no cache"""
        try:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            current_time = CacheManager._get_utc_now()
            expires_at = (current_time + timedelta(hours=ttl_hours)).isoformat()
            
            # Prepara a resposta para cache
            response_to_cache = {
                "text": response.get("text", ""),
                "model": model,
                "success": response.get("success", True)
            }
            
            # Usa upsert para lidar com entradas duplicadas
            supabase.table('response_cache').upsert({
                'prompt_hash': prompt_hash,
                'prompt': prompt,
                'response': json.dumps(response_to_cache),
                'model': model,
                'expires_at': expires_at,
                'last_accessed': current_time.isoformat(),
                'hit_count': 1
            }).execute()
            
            logger.info(f"Resposta cacheada com sucesso: {prompt_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {str(e)}")
            return False

    @staticmethod
    async def cleanup_expired_cache() -> int:
        """Remove entradas expiradas do cache"""
        try:
            current_time = CacheManager._get_utc_now().isoformat()
            response = supabase.table('response_cache').delete().lt('expires_at', current_time).execute()
            
            count = len(response.data) if response and response.data else 0
            logger.info(f"Limpeza de cache: {count} entradas removidas")
            return count
            
        except Exception as e:
            logger.error(f"Erro na limpeza do cache: {str(e)}")
            return 0

# Instância global do gerenciador
cache_manager = CacheManager() 