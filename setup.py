import sys
import os
from cx_Freeze import setup, Executable
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import time

# Definindo os arquivos adicionais que serão incluídos no executável
includefiles = [
    "C:/Users/arqui/OneDrive/Documentos/estoque/img",   # Imagens
    "C:/Users/arqui/OneDrive/Documentos/estoque/estoque.db",  # Banco de dados
    "C:/Users/arqui/OneDrive/Documentos/estoque/font/Helvetica-Bold.ttf",  # Fontes
    "C:/Users/arqui/OneDrive/Documentos/estoque/font/Helvetica.ttf"
]

# Definindo os pacotes que precisam ser incluídos (barcode, PIL)
includes = ["barcode", "PIL"]

# Função para criar a imagem do ícone
def create_image():
    # Carregar o ícone diretamente
    icon_path = "C:/Users/arqui/OneDrive/Documentos/estoque/img/supermarket.ico"
    image = Image.open(icon_path)
    return image

# Função que cria o ícone na bandeja do sistema
def on_quit(icon, item):
    icon.stop()

# Definindo o executável
executables = [Executable("controle_estoque.py", 
                          base="Win32GUI", 
                          target_name="EstoqueMax.exe", 
                          icon="C:/Users/arqui/OneDrive/Documentos/estoque/img/supermarket.ico")]

# Função para rodar o ícone da bandeja
def set_taskbar_icon():
    icon = Icon("Controle Estoque", create_image(), menu=Menu(MenuItem("Quit", on_quit)))
    icon.run()

# Configuração do cx_Freeze
setup(
    name="EstoqueMax",
    version="1.0",
    description="Sistema de controle de estoque",
    options={
        "build_exe": {
            "packages": includes,
            "include_files": includefiles,
            "optimize": 2,
        }
    },
    executables=executables
)

# Inicia a função que roda o ícone
if __name__ == "__main__":
    set_taskbar_icon()
