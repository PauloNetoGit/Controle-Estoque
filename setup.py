import sys
from cx_Freeze import setup, Executable

# Definindo os arquivos adicionais que serão incluídos no executável
includefiles = [
    "C:/Users/arqui/OneDrive/Documentos/estoque/img",   # Imagens
    "C:/Users/arqui/OneDrive/Documentos/estoque/estoque.db",  # Banco de dados
    "C:/Users/arqui/OneDrive/Documentos/estoque/font/Helvetica-Bold.ttf",  # Fontes
    "C:/Users/arqui/OneDrive/Documentos/estoque/font/Helvetica.ttf"
]

# Definindo os pacotes que precisam ser incluídos (barcode, PIL)
includes = ["barcode", "PIL"]

# Definindo o executável
executables = [Executable("controle_estoque.py", base="Win32GUI", target_name="controle_estoque.exe")]

# Configuração do cx_Freeze
setup(
    name="Controle Estoque",
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
