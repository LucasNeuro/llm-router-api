import asyncio
import sys
import os
import json
from loguru import logger
from dotenv import load_dotenv

# Adiciona diretório pai ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Carrega variáveis de ambiente
load_dotenv()

from utils.database import SupabaseManager


async def test_supabase_connection():
    """Testa conexão com Supabase e retorna estrutura das tabelas"""
    try:
        db = SupabaseManager()

        # Verifica estrutura das tabelas
        tables = ["response_cache", "message_queue", "conversation_context"]
        results = {}

        for table in tables:
            try:
                print(f"\n--- Verificando tabela {table} ---")
                # Tenta obter definição da tabela
                response = db.supabase.table(table).select("*").limit(1).execute()
                print(f"- Existe? {len(response.data) >= 0}")

                if len(response.data) > 0:
                    print(f"- Exemplo: {json.dumps(response.data[0], indent=2)}")

                results[table] = {
                    "exists": True,
                    "sample": response.data[0] if response.data else None,
                }
            except Exception as e:
                print(f"- Erro: {str(e)}")
                results[table] = {"exists": False, "error": str(e)}

        # Tenta inserir dados de teste
        print("\n--- Testando inserção ---")

        # Teste de cache
        try:
            await db.save_to_cache(
                prompt="Teste de cache",
                response={
                    "text": "Isto é um teste",
                    "model": "test_model",
                    "success": True,
                },
                model="test_model",
            )
            print("- Cache: Inserido com sucesso")
        except Exception as e:
            print(f"- Cache: Erro ao inserir - {str(e)}")

        # Teste de fila
        try:
            msg_id = await db.add_to_queue("test_sender", "Teste de fila")
            print(f"- Fila: Inserido com sucesso, ID: {msg_id}")

            # Atualiza status
            await db.update_queue_status(
                msg_id=msg_id,
                status="completed",
                response={"text": "Resposta de teste", "success": True},
            )
            print(f"- Fila: Status atualizado")
        except Exception as e:
            print(f"- Fila: Erro ao inserir - {str(e)}")

        # Teste de contexto
        try:
            await db.update_conversation_context(
                sender="test_sender",
                user_message="Olá",
                bot_response="Como posso ajudar?",
            )
            print("- Contexto: Inserido com sucesso")
        except Exception as e:
            print(f"- Contexto: Erro ao inserir - {str(e)}")

        print("\n--- Testes concluídos! ---")

    except Exception as e:
        print(f"Erro ao conectar ao Supabase: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_supabase_connection())
