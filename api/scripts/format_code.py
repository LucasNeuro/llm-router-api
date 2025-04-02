#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def main():
    """Formata todo o código Python no projeto."""
    # Encontra o diretório raiz do projeto
    root_dir = Path(__file__).parent.parent
    
    print("Formatando código com Black...")
    try:
        subprocess.run(["black", str(root_dir)], check=True)
        print("✓ Black concluído com sucesso")
    except subprocess.CalledProcessError:
        print("✗ Erro ao executar Black")
        sys.exit(1)
    
    print("\nVerificando código com Flake8...")
    try:
        subprocess.run(["flake8", str(root_dir)], check=True)
        print("✓ Flake8 concluído com sucesso")
    except subprocess.CalledProcessError:
        print("✗ Erros encontrados pelo Flake8")
        sys.exit(1)
    
    print("\n✓ Formatação concluída com sucesso!")

if __name__ == "__main__":
    main() 