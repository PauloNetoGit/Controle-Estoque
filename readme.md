# GERA O .SPEC E O .EXE
<code>pyinstaller estoqueMax.py</code>

# Executando o Build

<code>
pyinstaller --onefile --windowed --icon="img/supermarket.ico" --add-data "img;img" --add-data "estoque.db;." --add-data "font;font" --add-data "C:/Users/Teste/AppData/Local/Programs/Python/Python314/Lib/site-packages/barcode/fonts;barcode/fonts" --hidden-import "PIL" --hidden-import "barcode" --hidden-import "qrcode" --hidden-import "reportlab" estoqueMax.py
</code>
