import os
import sys
import asyncio
import json
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from api.utils.agent_service import agent_service
from api.models.agent import g4_agent
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

async def test_agent_response(message, sender_phone="5511999999999"):
    """Testa a resposta do agente para uma mensagem"""
    print(f"\n{'=' * 50}")
    print(f"📱 Mensagem do usuário ({sender_phone}):")
    print(f"{message}")
    print(f"{'=' * 50}\n")
    
    # Processa a mensagem com o agente
    result = await agent_service.process_message(
        agent_id="g4-telecom",
        message=message,
        sender_phone=sender_phone
    )
    
    print(f"🤖 Resposta de {result.get('agent_name', 'Geovana')} (usando {result.get('model', 'desconhecido')}):")
    print(f"{result['text']}")
    print(f"\nMetadados:")
    print(f"- Agente: {result.get('agent_id', 'g4-telecom')}")
    print(f"- Modelo usado: {result.get('model', 'desconhecido')}")
    print(f"- Necessita intervenção humana: {result.get('need_human', False)}")
    print(f"{'=' * 50}\n")
    
    return result

async def run_interactive_test():
    """Executa um teste interativo com o agente"""
    print(f"\n{'=' * 50}")
    print(f"🤖 Teste do Agente G4 Telecom - {g4_agent.config.name}")
    print(f"{'=' * 50}")
    print("Digite 'sair' para encerrar o teste.\n")
    
    sender_phone = input("Digite o número de telefone do remetente (ou Enter para usar padrão): ")
    if not sender_phone:
        sender_phone = "5511999999999"
    
    while True:
        message = input("\n📱 Digite sua mensagem: ")
        if message.lower() in ["sair", "exit", "quit"]:
            break
            
        await test_agent_response(message, sender_phone)

async def run_predefined_tests():
    """Executa testes com mensagens predefinidas"""
    test_messages = [
        "Oi, gostaria de saber sobre os planos de internet de vocês",
        "Qual o plano mais barato?",
        "E o plano de 1 Giga, quanto custa?",
        "Vocês têm pacotes com TV?",
        "Como funcionam as câmeras de segurança?",
        "Quero falar com um atendente humano"
    ]
    
    for message in test_messages:
        await test_agent_response(message)
        # Pequeno delay para evitar limitações de API
        await asyncio.sleep(1)

async def main():
    """Função principal"""
    # Escolha o modo de teste
    print("\nEscolha o modo de teste:")
    print("1. Interativo (digite suas próprias mensagens)")
    print("2. Predefinido (usa mensagens predefinidas)")
    
    choice = input("Escolha (1 ou 2): ")
    
    if choice == "1":
        await run_interactive_test()
    else:
        await run_predefined_tests()
    
    print("\nTeste concluído!")

if __name__ == "__main__":
    asyncio.run(main()) 