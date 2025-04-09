from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime, timedelta
from loguru import logger
from .supabase import supabase
import re
import uuid

class CacheManager:
    """Gerenciador de cache usando Supabase"""
    
    @staticmethod
    def _normalize_prompt(prompt: str) -> str:
        """Normaliza o prompt para busca"""
        # Remove pontuação e converte para minúsculas
        normalized = prompt.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = ' '.join(normalized.split())
        return normalized

    @staticmethod
    def _calculate_similarity(prompt1: str, prompt2: str) -> float:
        """Calcula similaridade entre prompts"""
        words1 = set(CacheManager._normalize_prompt(prompt1).split())
        words2 = set(CacheManager._normalize_prompt(prompt2).split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
            
        return len(intersection) / len(union)

    @staticmethod
    def _ensure_cache_table():
        """Garante que a tabela de cache existe"""
        try:
            # Verifica se a tabela existe
            supabase.table('response_cache').select('id').limit(1).execute()
            logger.info("Tabela de cache verificada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao verificar tabela de cache: {str(e)}")
            raise

    @staticmethod
    async def get_cached_response(prompt: str) -> Optional[Dict[str, Any]]:
        """Busca uma resposta no cache"""
        try:
            # Normaliza o prompt e gera o hash
            normalized_prompt = CacheManager._normalize_prompt(prompt)
            prompt_hash = hashlib.sha256(normalized_prompt.encode()).hexdigest()
            
            # Busca por match exato primeiro
            response = supabase.table('response_cache')\
                .select('*')\
                .eq('prompt_hash', prompt_hash)\
                .gt('expires_at', datetime.utcnow().isoformat())\
                .execute()
            
            if response and response.data and len(response.data) > 0:
                logger.info(f"Cache hit exato para prompt_hash: {prompt_hash}")
                cached_data = response.data[0]
                best_similarity = 1.0
            else:
                # Se não encontrou match exato, busca por similaridade
                response = supabase.table('response_cache')\
                    .select('*')\
                    .gt('expires_at', datetime.utcnow().isoformat())\
                    .execute()
                
                if not (response and response.data):
                    logger.info("Nenhuma entrada válida no cache")
                    return None
                
                # Procura por prompts similares
                best_match = None
                best_similarity = 0.0
                
                for entry in response.data:
                    similarity = CacheManager._calculate_similarity(prompt, entry['prompt'])
                    if similarity > 0.8 and similarity > best_similarity:  # 80% de similaridade mínima
                        best_similarity = similarity
                        best_match = entry
                
                if not best_match:
                    logger.info("Nenhum match similar encontrado no cache")
                    return None
                    
                logger.info(f"Cache hit por similaridade ({best_similarity:.2%}) para prompt: {best_match['prompt']}")
                cached_data = best_match
            
            try:
                # Atualiza hit_count e last_accessed
                update_data = {
                    'hit_count': cached_data['hit_count'] + 1,
                    'last_accessed': datetime.utcnow().isoformat()
                }
                
                supabase.table('response_cache')\
                    .update(update_data)\
                    .eq('id', cached_data['id'])\
                    .execute()
                
                # Processa a resposta do cache
                cached_response = cached_data['response']
                if isinstance(cached_response, str):
                    cached_response = json.loads(cached_response)
                
                return {
                    "text": cached_response.get("text", ""),
                    "model": cached_data['model'],
                    "success": True,
                    "from_cache": True,
                    "confidence": cached_response.get("confidence", 1.0),
                    "model_scores": cached_response.get("model_scores"),
                    "indicators": cached_response.get("indicators"),
                    "cache_similarity": best_similarity
                }
                
            except Exception as e:
                logger.error(f"Erro ao processar resposta do cache: {str(e)}")
                logger.exception("Stacktrace completo:")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar cache: {str(e)}")
            logger.exception("Stacktrace completo:")
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
            # Normaliza o prompt e gera o hash
            normalized_prompt = CacheManager._normalize_prompt(prompt)
            prompt_hash = hashlib.sha256(normalized_prompt.encode()).hexdigest()
            expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()
            
            # Prepara a resposta para cache
            response_to_cache = {
                "text": response.get("text", ""),
                "model": model,
                "success": response.get("success", True),
                "confidence": response.get("confidence", 1.0),
                "model_scores": response.get("model_scores", {}),
                "indicators": response.get("indicators", {})
            }
            
            # Verifica se já existe no cache
            existing = supabase.table("response_cache")\
                .select("*")\
                .eq("prompt_hash", prompt_hash)\
                .execute()
            
            if existing and existing.data:
                # Atualiza entrada existente
                data = {
                    "response": response_to_cache,
                    "last_accessed": datetime.utcnow().isoformat(),
                    "hit_count": existing.data[0].get("hit_count", 0) + 1
                }
                
                result = supabase.table("response_cache")\
                    .update(data)\
                    .eq("prompt_hash", prompt_hash)\
                    .execute()
            else:
                # Cria nova entrada
                data = {
                    "id": str(uuid.uuid4()),
                    "prompt_hash": prompt_hash,
                    "prompt": prompt,
                    "response": response_to_cache,
                    "model": model,
                    "expires_at": expires_at,
                    "last_accessed": datetime.utcnow().isoformat(),
                    "hit_count": 1,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                result = supabase.table("response_cache")\
                    .insert(data)\
                    .execute()
            
            logger.info(f"Cache {'atualizado' if existing and existing.data else 'criado'} com sucesso para hash: {prompt_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {str(e)}")
            logger.exception("Stacktrace completo:")
            return False

    @staticmethod
    async def cleanup_expired_cache() -> int:
        """Remove entradas expiradas do cache"""
        try:
            response = supabase.table('response_cache').delete().lt('expires_at', datetime.utcnow().isoformat()).execute()
            
            count = len(response.data) if response and response.data else 0
            logger.info(f"Limpeza de cache: {count} entradas removidas")
            return count
            
        except Exception as e:
            logger.error(f"Erro na limpeza do cache: {str(e)}")
            return 0

# Instância global do gerenciador
cache_manager = CacheManager() 