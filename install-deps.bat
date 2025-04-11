@echo off
echo ====== Criando ambiente virtual para testes ======
python -m venv .venv.test
call .venv.test\Scripts\activate

echo ====== Atualizando pip ======
pip install --upgrade pip
pip cache purge

echo ====== Instalando dependencias na ordem correta ======
:: Primeiro mistralai para estabelecer as dependências de httpx
pip install mistralai==0.0.12

:: Depois os outros pacotes
pip install openai==1.12.0
pip install supabase==1.0.3
pip install anthropic==0.18.1

:: Por fim, o resto dos requerimentos
pip install -r requirements.txt

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