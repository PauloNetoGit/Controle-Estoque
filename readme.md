# Gerando o .spec e o .exe
<code>pyinstaller estoqueMax.py</code>

# Executando o Build
<code>
pyinstaller --onefile --windowed --icon="img/supermarket.ico" --add-data "img;img" --add-data "font;font" --add-data "estoque.db;." --add-data "C:/Users/Teste/AppData/Local/Programs/Python/Python38/lib/site-packages/barcode/fonts;barcode/fonts" --add-data "escpos/capabilities;escpos/capabilities" --hidden-import=PIL --hidden-import=barcode --hidden-import=qrcode --hidden-import=reportlab --hidden-import=escpos estoqueMax.py
</code>

