@echo off
echo ===============================================
echo   Reiniciando ambiente de dependencias
echo ===============================================

:: Verifica se pip está instalado
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X pip nao encontrado. Por favor, instale o Python e o pip.
    exit /b 1
)

:: Desinstala todas as dependências atuais (exceto pip e setuptools)
echo Desinstalando dependencias atuais...
for /f "delims=" %%i in ('pip freeze ^| findstr /v "pip" ^| findstr /v "setuptools"') do (
    echo Desinstalando %%i
    pip uninstall -y %%i
)

:: Limpa o cache do pip
echo Limpando cache do pip...
pip cache purge

:: Atualiza o pip para a versão mais recente
echo Atualizando pip...
pip install --upgrade pip

:: Reinstala as dependências do requirements.txt
echo Instalando dependencias do requirements.txt...
pip install -r requirements.txt

echo Dependencias reinstaladas com sucesso!
echo =============================================== 