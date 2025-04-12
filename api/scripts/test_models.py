import asyncio
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from api.llm_router.gemini import call_gemini
from api.llm_router.mistral import call_mistral
from api.llm_router.deepseek import call_deepseek
from api.utils.logger import logger

async def test_model(name: str, call_func, test_prompt: str):
    """Testa um modelo específico"""
    logger.info(f"\n{'='*50}")
    logger.info(f"Testando modelo: {name}")
    logger.info(f"{'='*50}")
    
    try:
        response = await call_func(test_prompt)
        success = response.get("success", False)
        
        if success:
            logger.info(f"✅ {name} funcionando corretamente!")
            logger.info(f"Resposta: {response.get('text', '')[:100]}...")
        else:
            logger.error(f"❌ {name} falhou!")
            logger.error(f"Erro: {response.get('text', 'Sem mensagem de erro')}")
            
        logger.info(f"Detalhes completos: {response}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar {name}: {str(e)}")

async def main():
    """Função principal que testa todos os modelos"""
    logger.info("Iniciando testes dos modelos LLM")
    
    # Prompt de teste simples
    test_prompt = "Por favor, explique de forma breve o que é inteligência artificial."
    
    # Lista de modelos para testar
    models = [
        ("Gemini", call_gemini),
        ("Mistral", call_mistral),
        ("Deepseek", call_deepseek)
    ]
    
    # Testa cada modelo
    for model_name, model_func in models:
        await test_model(model_name, model_func, test_prompt)
        await asyncio.sleep(1)  # Pequena pausa entre os testes

    logger.info("\nTestes concluídos!")

if __name__ == "__main__":
    # Verifica se as variáveis de ambiente estão configuradas
    logger.info("Verificando variáveis de ambiente:")
    env_vars = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "GPT_API_KEY": os.getenv("GPT_API_KEY")
    }
    
    for var_name, value in env_vars.items():
        if value:
            masked_value = value[:8] + "..." + value[-4:]
            logger.info(f"✅ {var_name} configurada: {masked_value}")
        else:
            logger.warning(f"❌ {var_name} não encontrada!")
    
    # Executa os testes
    asyncio.run(main()) 