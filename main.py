"""
Ponto de entrada da aplicação.
"""

import sys
import os

# Adiciona o diretório src/ ao path para que os módulos internos sejam encontrados
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from src.gui.app import start_app

if __name__ == "__main__":
    start_app()
