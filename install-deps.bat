@echo off
echo ====== Criando ambiente virtual para testes ======
python -m venv .venv.test
call .venv.test\Scripts\activate

echo ====== Atualizando pip ======
pip install --upgrade pip
pip cache purge

echo ====== Instalando dependencias na ordem correta ======
:: Primeiro, instalar httpx na versão exigida pelo mistralai
pip install httpx==0.25.2

:: Instalar pacotes principais com --no-dependencies
pip install --no-dependencies mistralai==0.0.12
pip install --no-dependencies openai==1.12.0
pip install --no-dependencies supabase==1.0.3
pip install --no-dependencies anthropic==0.18.1

:: Instalar dependências comuns necessárias
pip install pydantic==2.11.3
pip install anyio==4.9.0
pip install sniffio==1.3.1
pip install typing-extensions==4.12.2
pip install certifi==2024.12.14
pip install orjson==3.10.15
pip install httpcore==1.0.7

:: Instalar o resto dos pacotes individualmente
pip install fastapi==0.109.2
pip install uvicorn==0.27.1
pip install python-dotenv==1.0.1
pip install neo4j==5.17.0
pip install google-generativeai==0.3.2
pip install requests==2.31.0
pip install tiktoken==0.5.2
pip install python-jose==3.3.0
pip install passlib==1.7.4
pip install bcrypt==4.1.2
pip install rich==13.7.0
pip install loguru==0.7.2
pip install python-json-logger==2.0.7
pip install tenacity==8.2.3

echo ====== Verificando versoes instaladas ======
pip list | findstr "httpx"
pip list | findstr "mistralai"
pip list | findstr "supabase"
pip list | findstr "anthropic"
pip list | findstr "openai"

echo ====== Teste completo ======
:: Desative o ambiente virtual
call deactivate

echo Para ativar o ambiente de teste, execute: .venv.test\Scripts\activate 