import os
import tempfile
import httpx
import base64
import uuid
import aiofiles
from typing import Optional, Dict, Any
from loguru import logger
from openai import OpenAI
from ..utils.supabase import supabase

GPT_API_KEY = os.getenv("GPT_API_KEY")

# Nome do bucket no Supabase Storage (usando o bucket existente)
SUPABASE_AUDIO_BUCKET = "audiomessages"  # Mantendo o nome exato como está no Supabase

class AudioService:
    """Serviço para converter texto em áudio e transcrição de áudio para texto com armazenamento em Supabase"""
    
    @staticmethod
    def get_temp_path(filename: str) -> str:
        """Retorna um caminho temporário seguro para o sistema operacional atual."""
        return os.path.join(tempfile.gettempdir(), filename)
    
    @staticmethod
    async def ensure_bucket_exists():
        """Verifica acesso ao bucket de áudio no Supabase Storage"""
        try:
            # Tenta listar o conteúdo do bucket para verificar acesso
            logger.info(f"Verificando acesso ao bucket '{SUPABASE_AUDIO_BUCKET}'...")
            supabase.storage.from_(SUPABASE_AUDIO_BUCKET).list()
            logger.info("Acesso ao bucket confirmado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao acessar bucket: {str(e)}")
            raise  # Re-lança o erro para ser tratado no nível acima
    
    @staticmethod
    async def text_to_speech(text: str, request_id: str) -> dict:
        """Converte texto para áudio usando a API OpenAI TTS."""
        temp_path = None
        try:
            # Verifica acesso ao bucket
            await AudioService.ensure_bucket_exists()
            
            client = OpenAI(api_key=GPT_API_KEY)
            if not GPT_API_KEY:
                raise ValueError("GPT_API_KEY não configurada")
                
            temp_path = AudioService.get_temp_path(f"tts_{request_id}.mp3")
            
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )
            
            # Salva o áudio localmente
            response.stream_to_file(temp_path)
            logger.info(f"Áudio gerado e salvo em: {temp_path}")
            
            # Upload para o Supabase
            with open(temp_path, "rb") as f:
                file_path = f"tts/{request_id}.mp3"
                supabase.storage.from_(SUPABASE_AUDIO_BUCKET).upload(
                    path=file_path,
                    file=f,
                    file_options={"content-type": "audio/mpeg"}
                )
                logger.info(f"Áudio enviado para Supabase: {file_path}")
            
            # Gera URL pública
            public_url = supabase.storage.from_(SUPABASE_AUDIO_BUCKET).get_public_url(f"tts/{request_id}.mp3")
            logger.info(f"Áudio disponível em: {public_url}")
            
            return {
                "local_path": temp_path,
                "public_url": public_url
            }
            
        except Exception as e:
            logger.error(f"Erro na conversão texto-fala: {str(e)}")
            raise
        finally:
            # Limpa o arquivo temporário se existir
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"Arquivo temporário removido: {temp_path}")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo temporário: {str(e)}")
    
    @staticmethod
    async def speech_to_text(audio_path: str, request_id: str) -> dict:
        """Transcreve áudio para texto usando a API OpenAI Whisper."""
        try:
            # Garante que o bucket existe
            await AudioService.ensure_bucket_exists()
            
            client = OpenAI(api_key=os.getenv("GPT_API_KEY"))
            
            # Upload para o Supabase
            with open(audio_path, "rb") as f:
                supabase.storage.from_(SUPABASE_AUDIO_BUCKET).upload(
                    path=f"stt/{request_id}.mp3",
                    file=f,
                    file_options={"content-type": "audio/mpeg"}
                )
            
            # Transcrição
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="text"
                )
            
            logger.info(f"Áudio transcrito com sucesso: {transcription[:100]}...")
            
            return {
                "text": transcription,
                "audio_path": audio_path
            }
            
        except Exception as e:
            logger.error(f"Erro na transcrição: {str(e)}")
            raise
    
    @staticmethod
    async def save_base64_to_file(base64_data: str, file_type: str = "mp3") -> Optional[str]:
        """
        Salva dados base64 em um arquivo temporário
        
        Args:
            base64_data: String com dados em base64
            file_type: Extensão do arquivo (mp3, ogg, etc)
            
        Returns:
            String com o caminho para o arquivo ou None em caso de erro
        """
        try:
            # Decodifica o base64
            audio_bytes = base64.b64decode(base64_data)
            
            # Cria um arquivo temporário
            file_id = str(uuid.uuid4())
            file_path = AudioService.get_temp_path(f"audio_{file_id}.{file_type}")
            
            # Salva no arquivo
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(audio_bytes)
                
            logger.info(f"Base64 salvo em arquivo temporário: {file_path}")
            return file_path
                
        except Exception as e:
            logger.error(f"Erro ao salvar base64 em arquivo: {str(e)}")
            return None
            
    @staticmethod
    async def get_audio_base64(file_path: str) -> Optional[str]:
        """
        Converte um arquivo de áudio para base64
        
        Args:
            file_path: Caminho para o arquivo de áudio
            
        Returns:
            String com o áudio em base64 ou None em caso de erro
        """
        try:
            async with aiofiles.open(file_path, "rb") as audio_file:
                audio_bytes = await audio_file.read()
                base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                return base64_audio
                
        except Exception as e:
            logger.error(f"Erro ao converter áudio para base64: {str(e)}")
            return None
    
    @staticmethod
    async def save_audio_metadata(audio_info: Dict[str, Any], conversation_id: Optional[str] = None) -> bool:
        """
        Salva metadados do áudio na tabela de metadados
        
        Args:
            audio_info: Informações do áudio
            conversation_id: ID da conversa relacionada
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Prepara os dados para inserção
            audio_data = {
                "file_id": audio_info.get("file_id"),
                "sender_phone": audio_info.get("sender_phone"),
                "storage_path": audio_info.get("storage_path"),
                "bucket": audio_info.get("bucket"),
                "url": audio_info.get("url"),
                "type": audio_info.get("type"),
                "conversation_id": conversation_id,
                "created_at": "now()"
            }
            
            # Insere no Supabase
            supabase.table("audio_metadata").insert(audio_data).execute()
            logger.info(f"Metadados do áudio salvos com sucesso: {audio_info.get('file_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar metadados do áudio: {str(e)}")
            return False
            
    @staticmethod
    def cleanup_temp_file(file_path: str) -> None:
        """Remove um arquivo temporário"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Arquivo temporário removido: {file_path}")
        except Exception as e:
            logger.error(f"Erro ao remover arquivo temporário: {str(e)}")

# Instância global do serviço
audio_service = AudioService() 