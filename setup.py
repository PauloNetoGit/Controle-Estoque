import sys
import os
from cx_Freeze import setup, Executable

# Arquivos incluídos
includefiles = [
    ("C:/Users/arqui/OneDrive/Documentos/estoque/img", "img"),
    "C:/Users/arqui/OneDrive/Documentos/estoque/estoque.db",
    ("C:/Users/arqui/OneDrive/Documentos/estoque/font/Helvetica-Bold.ttf", "Helvetica-Bold.ttf"),
    ("C:/Users/arqui/OneDrive/Documentos/estoque/font/Helvetica.ttf", "Helvetica.ttf"),
]

# Pacotes necessários
includes = ["barcode", "PIL", "pystray"]

executables = [
    Executable(
        "controle_estoque.py",
        base="Win32GUI",
        target_name="EstoqueMax.exe",
        icon="C:/Users/arqui/OneDrive/Documentos/estoque/img/supermarket.ico"
    )
]

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
