import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, Label
import os
import sys
import shutil
import sqlite3
import time
from pathlib import Path
from datetime import datetime

# --- Importações para a GUI (Pillow) ---
try:
    from PIL import Image, ImageTk 
except ImportError:
    Image = None
    ImageTk = None
    print("Atenção: A biblioteca Pillow (PIL) não está instalada. O logo e alguns ícones não serão exibidos.")
    
# --- Importações condicionais para Geração de PDF/Etiquetas ---
try:
    # Bibliotecas para geração de PDF e códigos
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm, inch
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    # Bibliotecas para códigos de barras
    import barcode
    from barcode.writer import ImageWriter
    import qrcode

except ImportError:
    # Se alguma dessas bibliotecas não estiver instalada, defina as variáveis como None
    canvas = None
    barcode = None
    qrcode = None
    pdfmetrics = None
    TTFont = None
    cm = None
    A4 = None
    SimpleDocTemplate = None # Adicionado para corrigir a ausência
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    getSampleStyleSheet = None
    colors = None
    print("Atenção: Bibliotecas de PDF/Etiquetas não encontradas. Instale-as (Pillow, python-barcode, qrcode, reportlab).")
    
# --- Constantes ---
SCAN_INCREMENT = 1 

# --- Funções de Caminho e Inicialização do DB ---

def resource_path(path):
    # Função para lidar com o caminho de recursos (útil para executáveis .exe)
    if hasattr(sys, '_MEIPASS'):  
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

def get_writable_db_path():
    # Define o caminho do banco de dados na pasta Documentos do usuário
    app_folder = Path(os.path.expanduser('~')) / 'Documents' / 'EstoqueMax'
    app_folder.mkdir(parents=True, exist_ok=True)
    return str(app_folder / "estoque.db")

project_db = resource_path("estoque.db")
db_path = get_writable_db_path()

# Copia o DB se for a primeira execução e houver um DB de projeto
if os.path.exists(project_db) and not os.path.exists(db_path):
    try:
        shutil.copyfile(project_db, db_path)
    except Exception:
        pass

# Paths de Recursos
icon_path = resource_path("img/supermarket.ico")
imagem_carrinho_path = resource_path("img/logo.png")
sobre_icon_path = resource_path("img/sobre.png")

# Tenta registrar a fonte Helvetica para o PDF (necessita do arquivo TTF)
if pdfmetrics is not None and TTFont is not None:
    try:
        # Assumindo que você tem um arquivo 'Helvetica.ttf'
        pdfmetrics.registerFont(TTFont('Helvetica', resource_path('font/Helvetica.ttf'))) 
    except Exception:
        # Se não houver, usa fontes padrão do ReportLab
        pass

# --- Funções de Banco de Dados (SQLite) ---
def criar_banco():
    db_path = get_writable_db_path()

    # 1. Tentar conectar ao DB no destino para verificar a integridade
    try:
        conn = sqlite3.connect(db_path)
        conn.close()
    except sqlite3.DatabaseError:
        # Se falhar, o DB no destino (Documentos) está malformado.
        print(f"ERRO: Banco de dados em {db_path} corrompido. Tentando restaurar...")
        
        # 2. Excluir o DB corrompido
        if os.path.exists(db_path):
            os.remove(db_path)
            print("Arquivo corrompido removido.")
            
        # 3. Forçar a cópia do DB de recurso interno
        project_db = resource_path("estoque.db")

        if os.path.exists(project_db):
            try:
                shutil.copyfile(project_db, db_path)
                print("Cópia de recurso bem-sucedida.")
            except Exception as e:
                print(f"Falha ao copiar o novo DB: {e}")
                
    # 4. Tentar a conexão final e criação da tabela
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Criação da tabela (seu SQL)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL DEFAULT 0,
                quantidade INTEGER NOT NULL DEFAULT 0,
                codigo_barras TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    except sqlite3.DatabaseError as e:
        print(f"ERRO CRÍTICO NO BANCO DE DADOS APÓS REPARO: {e}")
        raise # Levanta o erro para o usuário final.

# NOVO NOME: gerar_relatorio_estoque
def buscar_estoque_completo():
    """Busca todos os produtos cadastrados no banco de dados."""
    conn = None
    try:
        # 'db_path' deve ser uma variável global que aponta para o seu arquivo .db
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Consulta que seleciona todos os produtos.
        cursor.execute("SELECT id, nome, preco, quantidade, codigo_barras FROM produtos ORDER BY nome")
        produtos_estoque = cursor.fetchall()
        
        return produtos_estoque
        
    except Exception as e:
        print(f"Erro ao buscar estoque completo: {e}")
        # Retorna lista vazia em caso de erro para evitar quebrar o PDF
        return [] 
        
    finally:
        if conn:
            conn.close()

def buscar_produtos_faltantes():
    """Busca produtos com quantidade em estoque igual a zero."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Busca produtos onde a quantidade é 0 ou menor, ordenados por nome
        cursor.execute("SELECT id, nome, preco, quantidade, codigo_barras FROM produtos WHERE quantidade <= 0 ORDER BY nome")
        produtos_faltantes = cursor.fetchall()
        return produtos_faltantes
    except Exception as e:
        print(f"Erro ao buscar produtos faltantes: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
# --- NOVO: Gera o PDF de Estoque Completo ---
def gerar_relatorio_estoque():
    if canvas is None or SimpleDocTemplate is None:
        messagebox.showerror("Erro", "Bibliotecas para gerar PDF não estão instaladas (Instale: reportlab).")
        return

    # 1. Obter a lista completa de produtos
    estoque_completo = buscar_estoque_completo()
    
    if not estoque_completo:
        messagebox.showinfo("Relatório", "Nenhum produto cadastrado no estoque.")
        return

    # 2. Configuração do PDF
    pasta_relatorios = os.path.join(os.path.expanduser('~'), 'Documents', 'Relatorios_EstoqueMax')
    os.makedirs(pasta_relatorios, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(pasta_relatorios, f'Relatorio_Atual.pdf')
    
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        topMargin=50,
        bottomMargin=30,
        leftMargin=30,
        rightMargin=30
    )
    story = []
    
    # Estilos de Tabela e Título
    styles = getSampleStyleSheet()
    
    # 3. Cabeçalho do Relatório
    titulo = Paragraph("<b>RELATÓRIO COMPLETO DE ESTOQUE</b>", styles['h1'])
    story.append(titulo)
    story.append(Spacer(1, 12))
    
    data_relatorio = Paragraph(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal'])
    story.append(data_relatorio)
    story.append(Spacer(1, 12))
    
    # 4. Dados da Tabela
    # Cabeçalho da tabela
    data = [
        [
            Paragraph('<b>ID</b>', styles['Normal']), 
            Paragraph('<b>Nome do Produto</b>', styles['Normal']), 
            Paragraph('<b>Preço (R$)</b>', styles['Normal']), 
            Paragraph('<b>Quantidade</b>', styles['Normal']),
            Paragraph('<b>Código de Barras</b>', styles['Normal'])
        ]
    ]
    
    # Adiciona os dados dos produtos
    for idp, nome, preco, quantidade, cod in estoque_completo:
        preco_formatado = f"R$ {preco:.2f}".replace('.', ',')
        # Destaca itens com estoque zero ou negativo
        style_row = styles['Normal']
        if quantidade <= 0:
            style_row = styles['h5'] # Usa um estilo que você pode definir como vermelho se quiser
            
        data.append([
            idp, 
            Paragraph(nome, style_row), 
            preco_formatado, 
            quantidade, 
            cod
        ])
        
    # Configuração de estilo da tabela
    tabela = Table(data, colWidths=[30, 200, 80, 70, 100])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(tabela)
    
    # 5. Gera o documento
    try:
        doc.build(story)
        messagebox.showinfo("Sucesso", f"Relatório de Estoque Completo gerado e salvo em:\n{pdf_path}")
    except Exception as e:
        messagebox.showerror("Erro ao Gerar PDF", f"Falha ao gerar o relatório: {e}")


def adicionar_produto(nome, preco, quantidade, codigo_barras):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantidade FROM produtos WHERE codigo_barras = ?", (codigo_barras,))
    existente = cursor.fetchone()
    
    if existente:
        idp, qt_atual = existente
        nova_qt = qt_atual + quantidade
        # Atualiza nome, preço e incrementa a quantidade
        cursor.execute("UPDATE produtos SET nome = ?, preco = ?, quantidade = ? WHERE id = ?", (nome, preco, nova_qt, idp))
    else:
        cursor.execute("INSERT INTO produtos (nome, preco, quantidade, codigo_barras) VALUES (?, ?, ?, ?)",
                         (nome, preco, quantidade, codigo_barras))
    conn.commit()
    conn.close()

def editar_produto(id_produto, nome, preco, quantidade, codigo_barras):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE produtos SET nome = ?, preco = ?, quantidade = ?, codigo_barras = ? WHERE id = ?",
                     (nome, preco, quantidade, codigo_barras, id_produto))
    conn.commit()
    conn.close()

def remover_produto(id_produto, quantidade_remover):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT quantidade FROM produtos WHERE id = ?", (id_produto,))
    row = cursor.fetchone()
    if not row:
        messagebox.showerror("Erro", "Produto não encontrado!")
        conn.close()
        return
    quantidade_estoque = row[0]
    if quantidade_remover > quantidade_estoque:
        messagebox.showerror("Erro", "Quantidade a remover é maior que o estoque disponível.")
        conn.close()
        return
    nova_quantidade = quantidade_estoque - quantidade_remover
    if nova_quantidade <= 0: # Corrigido para excluir se a nova quantidade for zero ou negativa
        cursor.execute("DELETE FROM produtos WHERE id = ?", (id_produto,))
    else:
        cursor.execute("UPDATE produtos SET quantidade = ? WHERE id = ?", (nova_quantidade, id_produto))
    conn.commit()
    conn.close()
    messagebox.showinfo("Sucesso", "Operação realizada com sucesso!")

def buscar_produto_por_codigo(codigo_barras):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, preco, quantidade, codigo_barras FROM produtos WHERE codigo_barras = ?", (codigo_barras,))
    row = cursor.fetchone()
    conn.close()
    return row

def excluir_todos_dados_confirmado(treeview):
    resposta = messagebox.askyesno("Atenção", "Tem certeza que deseja excluir TODOS os dados do banco? Esta ação é irreversível.")
    if not resposta:
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='produtos'")
    conn.commit()
    conn.close()
    exibir_lista_produtos(treeview)
    messagebox.showinfo("Sucesso", "Todos os dados foram excluídos.")

def gerar_etiqueta(id_produto, quantidade_impressao, tipo="code128"):
    # Verifica se as bibliotecas estão carregadas
    if canvas is None or Image is None or barcode is None or qrcode is None:
        messagebox.showerror("Erro", "Bibliotecas para gerar etiquetas não estão instaladas (Instale: Pillow, python-barcode, qrcode, reportlab).")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT nome, codigo_barras FROM produtos WHERE id = ?", (id_produto,))
    produto = cursor.fetchone()
    conn.close()
    if not produto:
        messagebox.showerror("Erro", "Produto não encontrado!")
        return
        
    nome, codigo_barras = produto
    
    pasta = os.path.join(os.path.expanduser('~'), 'Documents', 'Etiquetas-controle-de-estoque')
    pasta_imagens = os.path.join(pasta, 'etiquetas_png')
    pasta_pdfs = os.path.join(pasta, 'etiquetas_pdf')
    os.makedirs(pasta_imagens, exist_ok=True)
    os.makedirs(pasta_pdfs, exist_ok=True)
    
    # Valores dimensionais (em cm, ajustados para milímetros em ReportLab)
    largura_etiqueta_final = 3.5 * cm
    altura_etiqueta_final = 2.0 * cm
    colunas, linhas = 5, 6
    
    imagem_path = None
    try:
        # Geração da imagem do código de barras
        if tipo.lower() in ("code128", "ean13") and barcode:
            code_type = "code128" if tipo.lower() == "code128" else "ean13"
            
            if code_type == "ean13" and len(codigo_barras) not in (12, 13):
                 messagebox.showerror("Erro", "Código de barras inválido para EAN13. Requer 12 ou 13 dígitos.")
                 return
                 
            barcode_class = barcode.get_barcode_class(code_type)
            # Ajuste de dimensões para a imagem do código de barras
            writer = ImageWriter()
            writer.set_options({'module_width': 0.2, 'module_height': 5.0, 'font_size': 8, 'text_distance': 3.0})
            
            barcode_instance = barcode_class(codigo_barras, writer=writer)
            caminho = os.path.join(pasta_imagens, f'{nome}__Id={id_produto}')
            barcode_instance.save(caminho) 
            imagem_path = f"{caminho}.png"
            
        elif tipo.lower() == "qrcode" and qrcode:
            imagem_path = os.path.join(pasta_imagens, f'{nome}__Id={id_produto}.png')
            # Ajuste para QR Code
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=2)
            qr.add_data(codigo_barras)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(imagem_path)
            altura_etiqueta_final = largura_etiqueta_final # QR Code é quadrado
        else:
            messagebox.showerror("Erro", "Tipo de código inválido ou bibliotecas faltando.")
            return
    except Exception as e:
        print(f"ERRO DE GERAÇÃO DE ETIQUETA: {e}") 
        messagebox.showerror("Erro", f"Erro ao gerar imagem do código. Verifique se o código é válido para o tipo selecionado: {e}")
        return

    pdf_path = os.path.join(pasta_pdfs, f'{nome}__Id={id_produto}_{tipo}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=A4)
    page_width, page_height = A4
    
    # Configurações de layout A4
    margem_horizontal = 20
    margem_vertical = 20
    margem_superior_inicial = page_height - 60 
    
    # --- Desenha o Cabeçalho da Primeira Página ---
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(page_width / 2, page_height - 30, f"Etiquetas para: {nome}")
    c.line(20, page_height - 40, page_width - 20, page_height - 40)
    
    
    largura_area_util = page_width - 2 * margem_horizontal
    altura_area_util = margem_superior_inicial - margem_vertical
    espacamento_x = largura_area_util / colunas
    espacamento_y = altura_area_util / linhas

    offset_x = (espacamento_x - largura_etiqueta_final) / 2
    offset_y = (espacamento_y - altura_etiqueta_final) / 2

    for i in range(quantidade_impressao):
        col = i % colunas
        row = (i // colunas) % linhas
        
        # Se for o início de uma nova página (exceto a primeira)
        if i > 0 and i % (colunas * linhas) == 0:
            c.showPage()
            # Desenha o título nas páginas subsequentes
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(page_width / 2, page_height - 30, f"Etiquetas para: {nome} (Cont.)")
            c.line(20, page_height - 40, page_width - 20, page_height - 40)
            
        x_grid_base = margem_horizontal + col * espacamento_x
        y_grid_base = margem_vertical + (linhas - 1 - row) * espacamento_y
        
        x_code = x_grid_base + offset_x
        y_code = y_grid_base + offset_y 

        # Desenha a imagem do código (ou QR)
        c.drawImage(imagem_path, x_code, y_code, width=largura_etiqueta_final, height=altura_etiqueta_final)

        # Contador e Nome do Produto abaixo do código de barras
        contador_texto = f"{i + 1}/{quantidade_impressao}"
        
        c.setFont("Helvetica", 8)
        x_nome = x_grid_base + espacamento_x / 2
        y_nome = y_code - 8
        c.drawCentredString(x_nome, y_nome, nome) # Desenha o nome
        
        c.setFont("Helvetica", 6) # Fonte menor para o contador
        y_contador = y_nome - 8
        c.drawCentredString(x_nome, y_contador, contador_texto) # Desenha o contador (ex: 1/100)
             
    c.save()
    messagebox.showinfo("Sucesso", f"Etiquetas geradas e salvas em:\n{pdf_path}")

def exibir_lista_produtos(treeview, termo_busca=""):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if termo_busca:
        termo = f"%{termo_busca.lower()}%"
        cursor.execute("SELECT id, nome, preco, quantidade, codigo_barras FROM produtos WHERE LOWER(nome) LIKE ? OR codigo_barras LIKE ? ORDER BY nome", (termo, termo))
    else:
        cursor.execute("SELECT id, nome, preco, quantidade, codigo_barras FROM produtos ORDER BY nome")
    produtos = cursor.fetchall()
    conn.close()
    for item in treeview.get_children():
        treeview.delete(item)
    for produto in produtos:
        idp, nome, preco, quantidade, cod = produto # Quantidade é o 4º item (INTEGER do DB)
    
        try:
            # Formatação de moeda: R$ 0,00
            preco_format = f"R$ {preco:.2f}".replace('.', ',')
        except Exception:
            preco_format = "R$ 0,00"
        # Destaca itens com estoque zero ou negativo
        tag = 'estoque_baixo' if quantidade <= 0 else ''
        # Aqui, você insere o valor bruto de 'quantidade' na célula do Treeview
        treeview.insert('', 'end', values=(idp, nome, preco_format, quantidade, cod), tags=(tag,))
        
def mostrar_contato(root):
    popup = Toplevel(root) 
    popup.title("Contato")
    popup.geometry("250x120")
    popup.grab_set()
    content = tk.Frame(popup, padx=20, pady=20)
    content.pack(fill="both", expand=True)
    Label(content, text="Entre em Contato: Paulo Neto\nTelefone/ZAP: (81) 9 8553-5360", justify="center").pack(pady=10)
    popup.resizable(False, False)

def limpar_campos(nome_entry, preco_entry, quantidade_entry, codigo_barras_entry, 
                     id_produto_remover_entry, quantidade_remover_entry, 
                     id_produto_imprimir_entry, quantidade_impressao_entry):
    
    nome_entry.delete(0, tk.END)
    preco_entry.delete(0, tk.END)
    quantidade_entry.delete(0, tk.END)
    codigo_barras_entry.delete(0, tk.END)
    
    id_produto_remover_entry.delete(0, tk.END)
    quantidade_remover_entry.delete(0, tk.END)
    id_produto_imprimir_entry.delete(0, tk.END)
    quantidade_impressao_entry.delete(0, tk.END)
    
    # Reseta a quantidade para 0 ou 1, dependendo da função
    quantidade_remover_entry.insert(0, "1")
    quantidade_impressao_entry.insert(0, "10")


# --- Função Principal da Interface (interface) ---

def interface():
    # --- Variáveis Globais/Locais (Escopo Interface) ---
    global nome_entry, preco_entry, quantidade_entry, codigo_barras_entry
    global codigo_caixa_entry, quantidade_caixa_entry 
    global root, aba_estoque, treeview_venda 
    global id_produto_remover_entry, quantidade_remover_entry
    global id_produto_imprimir_entry, quantidade_impressao_entry
    global treeview, notebook, total_label, status_venda_label 
    global valor_recebido_entry, troco_label, busca_entry
    global ordenar # Variável global de ordenação da Treeview
    global venda_atual # Lista que guarda os itens da venda
    
    root = tk.Tk()
    root.title("Controle de Estoque - Criado por: Paulo Neto")
    
    # --- CONFIGURAÇÕES DA JANELA ---
    try:
        root.iconbitmap(icon_path)
    except Exception:
        pass
        
    root.minsize(900, 600)
    
    style = ttk.Style(root) 
    style.theme_use('clam') 
    
    # Configurar tags da Treeview para estoque baixo (cor vermelha)
    style.configure("estoque_baixo", foreground="#E74C3C", font=('Helvetica', 9, 'bold'))

    # ---------------------------------------------------

    # --- CABEÇALHO COM IMAGEM E TÍTULO ---
    imagem_carrinho = None
    if Image and ImageTk:
        header_frame = tk.Frame(root, pady=5, padx=10, bg="#f5f5f5") # Fundo leve para destacar o cabeçalho
        header_frame.pack(side="top", fill="x")
        header_frame.columnconfigure(2, weight=1)
        
        try:
            # Carrega e redimensiona a imagem do carrinho
            img_pil = Image.open(imagem_carrinho_path)
            img_resized = img_pil.resize((130, 130), Image.LANCZOS) # Reduzindo para 90x90
            imagem_carrinho = ImageTk.PhotoImage(img_resized)
            
            imagem_label = tk.Label(header_frame, image=imagem_carrinho, bg="#f5f5f5")
            imagem_label.image = imagem_carrinho # Mantém a referência
            imagem_label.grid(row=0, column=0, padx=10, sticky="w")
        except Exception:
            # Caso a imagem não carregue, apenas avisa e segue
            tk.Label(header_frame, text="[LOGO AQUI]", font=("Helvetica", 12), bg="#f5f5f5").grid(row=0, column=0, padx=10, sticky="w")
            
        titulo_sub_frame = tk.Frame(header_frame, bg="#f5f5f5")
        titulo_sub_frame.grid(row=0, column=1, padx=10, sticky="w")
        
        botao_relatorio_frame = tk.Frame(header_frame, bg="#f5f5f5")
        botao_relatorio_frame.grid(row=0, column=2, sticky="e", padx=20)
        
        titulo = tk.Label(titulo_sub_frame, text="D&J - Sabor do sertão", font=("Helvetica", 24, "bold"), fg="#422717", bg="#f5f5f5")
        titulo.pack(anchor="w")
        
        subtitulo1 = tk.Label(titulo_sub_frame, text="Controle de Estoque e Venda - Gestão Eficiente", font=("Helvetica", 14), fg="#c7681b", bg="#f5f5f5")
        subtitulo1.pack(anchor="w")
        
    else:
        # Se PIL não estiver instalada, insere um título simples
        tk.Label(root, text="D&J Controle de Estoque", font=("Helvetica", 18, "bold"), fg="#fc6500").pack(pady=10)
    # --- FIM DO CABEÇALHO ---
    
    
    # Variáveis de controle do Scanner e Ordenação
    codigo_barras_sendo_lido = ""
    ultimo_timestamp = 0
    INTERVALO_MAXIMO_LEITURA = 0.15 
    
    ordenar = {"id": True, "nome": True, "preco": True, "quantidade": True, "codigo_barras": True}
    codigo_tipo = tk.StringVar(root, value="code128") # Variável para os Radiobuttons
    
    # Variável de controle da lista de venda
    venda_atual = [] 
    
    # --- FUNÇÕES DA CAIXA REGISTRADORA ---
    
    def calcular_total():
        total = sum(item['subtotal'] for item in venda_atual)
        total_str = f"R$ {total:.2f}".replace('.', ',')
        total_label.config(text=f"TOTAL: {total_str}")
        return total
    
    def calcular_troco():
        try:
            total_venda = calcular_total() # Pega o total atual da lista
            valor_pago_str = valor_recebido_entry.get().strip().replace(',', '.')
            valor_pago = float(valor_pago_str)
            
            if valor_pago < total_venda:
                troco_label.config(text="❌ Valor Insuficiente!", fg="#E74C3C")
                return

            troco = valor_pago - total_venda
            troco_formatado = f"R$ {troco:.2f}".replace('.', ',')
            
            troco_label.config(text=f"✅ Troco: {troco_formatado}", fg="#04AA6D")

        except ValueError:
            troco_label.config(text="⚠️ Entrada Inválida", fg="#F39C12")
            # Nao exibe messagebox aqui para nao atrapalhar a leitura em tempo real
        except NameError:
             messagebox.showerror("Erro", "O campo 'Valor Recebido' ou 'Troco' não foi inicializado corretamente.")
             
    def finalizar_venda():
        if not venda_atual:
            messagebox.showwarning("Atenção", "A lista de venda está vazia.")
            return

        total_venda = calcular_total()
        valor_pago_str = valor_recebido_entry.get().strip().replace(',', '.')
        
        try:
            valor_pago = float(valor_pago_str)
        except ValueError:
            messagebox.showerror("Erro", "Valor recebido inválido.")
            return

        if valor_pago < total_venda:
            messagebox.showerror("Erro", "O valor recebido é insuficiente para finalizar a venda.")
            return
            
        resposta = messagebox.askyesno("Confirmar Venda", f"Finalizar venda no valor de R$ {total_venda:.2f}?")
        
        if resposta:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            venda_sucesso = True
            itens_vendidos = []

            for item in venda_atual:
                try:
                    # Tenta dar baixa no estoque
                    cursor.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ? AND quantidade >= ?", 
                                   (item['quantidade'], item['id_db'], item['quantidade']))
                    if cursor.rowcount == 0:
                        # Se falhar (estoque insuficiente após a verificação inicial, mas antes do commit)
                        messagebox.showwarning("Estoque Esgotado", f"Falha ao dar baixa em {item['nome']}. Estoque insuficiente.")
                        venda_sucesso = False
                        break # Aborta o processo de baixa
                    
                    # Se a baixa for bem-sucedida, adiciona à lista de itens vendidos
                    itens_vendidos.append(item)
                    
                    # Se a quantidade for zerada, remove o produto (limpeza)
                    cursor.execute("DELETE FROM produtos WHERE id = ? AND quantidade <= 0", (item['id_db'],))
                    
                except Exception as e:
                    messagebox.showerror("Erro de DB", f"Erro ao atualizar o estoque: {e}")
                    venda_sucesso = False
                    break

            if venda_sucesso:
                conn.commit()
                conn.close()
                
                # Prepara o recibo
                troco = valor_pago - total_venda
                recibo_itens = "\n".join([f"{i['nome'][:20]:<20} {i['quantidade']:>3} x R$ {i['preco']:.2f} = R$ {i['subtotal']:.2f}" for i in itens_vendidos])
                
                recibo = (
                    f"========== VENDA FINALIZADA ==========\n"
                    f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"--------------------------------------\n"
                    f"{recibo_itens}\n"
                    f"--------------------------------------\n"
                    f"TOTAL:           R$ {total_venda:.2f}\n"
                    f"Valor Recebido:  R$ {valor_pago:.2f}\n"
                    f"TROCO:           R$ {troco:.2f}\n"
                    f"======================================\n"
                )
                
                messagebox.showinfo("Sucesso na Venda", recibo)
                
                # Limpa a interface de venda
                venda_atual.clear()
                atualizar_lista_venda()
                troco_label.config(text="✅ Troco: R$ 0,00", fg="#04AA6D")
                valor_recebido_entry.delete(0, tk.END)
                status_venda_label.config(text="Venda finalizada. Pronto.")
                
                # Recarrega a lista de estoque, caso o usuário volte para a aba
                exibir_lista_produtos(treeview)
                
            else:
                conn.rollback() # Reverte as alterações se houve erro na baixa
                conn.close()
                messagebox.showerror("Erro", "Venda abortada devido a erro de estoque/DB. Tente novamente.")


    def atualizar_lista_venda():
        for item in treeview_venda.get_children():
            treeview_venda.delete(item)
        
        for item in venda_atual:
            preco_format = f"R$ {item['preco']:.2f}".replace('.', ',')
            subtotal_format = f"R$ {item['subtotal']:.2f}".replace('.', ',')
            treeview_venda.insert('', 'end', values=(
                item['nome'], 
                preco_format, 
                item['quantidade'], 
                subtotal_format,
                item['codigo_barras']
            ))
        calcular_total()
        
    def ler_produto_venda(event=None):
        codigo = codigo_caixa_entry.get().strip()
        qt_str = quantidade_caixa_entry.get().strip() or "1" 
        
        if not codigo or not codigo.isdigit() or not qt_str.isdigit():
            status_venda_label.config(text="Erro: Código ou Quantidade inválida.")
            return

        quantidade_desejada = int(qt_str)
        if quantidade_desejada <= 0:
            status_venda_label.config(text="Erro: Quantidade deve ser positiva.")
            return

        # 1. Busca no Banco de Dados
        produto_db = buscar_produto_por_codigo(codigo)
        
        if not produto_db:
            status_venda_label.config(text="Erro: Produto não encontrado no estoque.")
            codigo_caixa_entry.delete(0, tk.END)
            return

        id_db, nome_db, preco_db, estoque_db, cod_db = produto_db
        preco_db = float(preco_db)
        
        # 2. Verifica estoque
        
        qtd_atual_na_venda = sum(item['quantidade'] for item in venda_atual if item['codigo_barras'] == codigo)
        quantidade_total_desejada = qtd_atual_na_venda + quantidade_desejada
        
        if estoque_db < quantidade_total_desejada:
            quantidade_disponivel_para_add = estoque_db - qtd_atual_na_venda

            if quantidade_disponivel_para_add > 0:
                messagebox.showwarning("Estoque Baixo", 
                                       f"Apenas {quantidade_disponivel_para_add} unidades de {nome_db} podem ser adicionadas. ")
                quantidade_a_adicionar = quantidade_disponivel_para_add
            else:
                messagebox.showwarning("Estoque Esgotado", 
                                       f"Estoque zerado ou limite atingido para {nome_db}.")
                status_venda_label.config(text=f"Limite de estoque para {nome_db} atingido na lista.")
                codigo_caixa_entry.delete(0, tk.END)
                quantidade_caixa_entry.delete(0, tk.END)
                quantidade_caixa_entry.insert(0, "1")
                return
        else:
            quantidade_a_adicionar = quantidade_desejada 
            
        
        # 3. Adiciona/Atualiza na lista de venda (venda_atual)
        item_existente = None
        for item in venda_atual:
            if item['codigo_barras'] == codigo:
                item_existente = item
                break

        subtotal_adicional = preco_db * quantidade_a_adicionar
        
        if item_existente:
            item_existente['quantidade'] += quantidade_a_adicionar
            item_existente['subtotal'] += subtotal_adicional
            status_venda_label.config(text=f"{nome_db} (x{quantidade_a_adicionar}) adicionado. Subtotal: R$ {subtotal_adicional:.2f}")

        else:
            venda_atual.append({
                'id_db': id_db,
                'nome': nome_db,
                'preco': preco_db,
                'quantidade': quantidade_a_adicionar,
                'codigo_barras': cod_db,
                'subtotal': subtotal_adicional
            })
            status_venda_label.config(text=f"Novo item: {nome_db} (x{quantidade_a_adicionar}). Subtotal: R$ {subtotal_adicional:.2f}")

        # Atualiza a interface
        atualizar_lista_venda()
        
        # Reseta o cálculo do troco e limpa o campo de valor recebido
        troco_label.config(text="✅ Troco: R$ 0,00", fg="#04AA6D")
        valor_recebido_entry.delete(0, tk.END)
            
        # GARANTE QUE A QUANTIDADE VOLTE PARA 1 APÓS A LEITURA
        codigo_caixa_entry.delete(0, tk.END)
        quantidade_caixa_entry.delete(0, tk.END) 
        quantidade_caixa_entry.insert(0, "1") 
        codigo_caixa_entry.focus_set()


    def remover_item_venda():
        selected = treeview_venda.selection()
        if not selected:
            messagebox.showerror("Erro", "Selecione um item para remover.")
            return
        
        try:
            # Pega o Código de Barras da coluna oculta
            cod_barras_remover = treeview_venda.item(selected[0], "values")[4] 
            
            # Percorre a lista de venda_atual e remove o item correspondente
            for i, item in enumerate(venda_atual):
                if item['codigo_barras'] == cod_barras_remover:
                    venda_atual.pop(i)
                    status_venda_label.config(text=f"Item removido da venda: {item['nome']}")
                    break
                    
        except IndexError:
            messagebox.showerror("Erro", "Erro ao identificar o item selecionado.")
            return
        
        atualizar_lista_venda()
        # Reseta o cálculo do troco e limpa o campo de valor recebido
        troco_label.config(text="✅ Troco: R$ 0,00", fg="#04AA6D")
        valor_recebido_entry.delete(0, tk.END)
        
    # --- FIM DAS FUNÇÕES DA CAIXA REGISTRADORA ---
    
    # --- Funções Auxiliares da Aba Estoque ---
    
    def gerar_etiqueta_btn_interna():
        # Função wrapper para passar os parâmetros para gerar_etiqueta
        imprimir_produto_btn() 
        
    def ordenar_lista(treeview, coluna):
        # Converte o nome da coluna para o nome do campo no DB
        coluna_db = {'id': 'id', 'nome': 'nome', 'preco': 'preco', 'quantidade': 'quantidade', 'codigo_barras': 'codigo_barras'}.get(coluna)
        if not coluna_db:
            return # Coluna não mapeada
        
        ordem = ordenar.get(coluna, True)
        ordenar[coluna] = not ordem
        
        direcao = 'ASC' if ordem else 'DESC'
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # O SQL já está correto
        cursor.execute(f"SELECT id, nome, preco, quantidade, codigo_barras FROM produtos ORDER BY {coluna_db} {direcao}")
        
        produtos = cursor.fetchall()
        conn.close()
        
        for item in treeview.get_children():
            treeview.delete(item)
            
        for produto in produtos:
            idp, nome, preco, quant, cod = produto
            try:
                preco_format = f"R$ {preco:.2f}".replace('.', ',')
            except Exception:
                preco_format = "R$ 0,00"
            
            tag = 'estoque_baixo' if quant <= 0 else ''
            treeview.insert('', 'end', values=(idp, nome, preco_format, quant, cod), tags=(tag,))


    def adicionar_produto_btn():
        _limpar_campos_estoque = lambda: limpar_campos(
            nome_entry, preco_entry, quantidade_entry, codigo_barras_entry, 
            id_produto_remover_entry, quantidade_remover_entry, 
            id_produto_imprimir_entry, quantidade_impressao_entry
        )
        
        nome = nome_entry.get().strip()
        preco_str = preco_entry.get().strip().replace(',', '.')
        codigo_barras = codigo_barras_entry.get().strip()
        if not nome or not codigo_barras or not preco_str:
            messagebox.showerror("Erro", "Nome, Preço e Código de Barras são obrigatórios.")
            return
        if not codigo_barras.isdigit():
            messagebox.showerror("Erro", "Código de Barras deve conter apenas dígitos.")
            return
        try:
            quantidade = int(quantidade_entry.get())
            preco = float(preco_str)
            if quantidade < 0:
                messagebox.showerror("Erro", "Quantidade não pode ser negativa (use 'Remover Estoque' para baixa).")
                return
            if preco < 0:
                messagebox.showerror("Erro", "Preço não pode ser negativo.")
                return
            
            # Se a quantidade for zero, apenas edita/atualiza o preço. Se for positiva, incrementa.
            if quantidade == 0:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM produtos WHERE codigo_barras = ?", (codigo_barras,))
                existente = cursor.fetchone()
                
                if existente:
                    # Se o produto existe, apenas atualiza nome e preço (mantém a quantidade)
                    cursor.execute("UPDATE produtos SET nome = ?, preco = ? WHERE id = ?", (nome, preco, existente[0]))
                    conn.commit()
                    messagebox.showinfo("Sucesso", "Produto atualizado (Estoque mantido).")
                else:
                    # Se não existe e a quantidade é 0, adiciona com estoque 0
                    adicionar_produto(nome, preco, 0, codigo_barras)
                    messagebox.showinfo("Sucesso", "Novo produto cadastrado com estoque 0.")
                conn.close()
            else:
                 adicionar_produto(nome, preco, quantidade, codigo_barras)
                 messagebox.showinfo("Sucesso", "Produto adicionado/atualizado (Estoque incrementado).")
            
            exibir_lista_produtos(treeview)
            _limpar_campos_estoque() 
        except ValueError:
            messagebox.showerror("Erro", "Quantidade/Preço inválidos (devem ser números).")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar produto: {e}")


    def editar_produto_btn():
        _limpar_campos_estoque = lambda: limpar_campos(
            nome_entry, preco_entry, quantidade_entry, codigo_barras_entry, 
            id_produto_remover_entry, quantidade_remover_entry, 
            id_produto_imprimir_entry, quantidade_impressao_entry
        )
        try:
            selected = treeview.selection()
            if not selected:
                messagebox.showerror("Erro", "Selecione um produto na lista para editar.")
                return
            idp = int(treeview.item(selected[0], "values")[0])
        except Exception:
            messagebox.showerror("Erro", "Seleção inválida.")
            return
        
        nome = nome_entry.get().strip()
        preco_str = preco_entry.get().strip().replace(',', '.')
        codigo_barras = codigo_barras_entry.get().strip()
        if not nome or not codigo_barras or not preco_str:
            messagebox.showerror("Erro", "Nome, Preço e Código de Barras são obrigatórios.")
            return
        if not codigo_barras.isdigit():
            messagebox.showerror("Erro", "Código de Barras deve ter apenas dígitos.")
            return
        try:
            quantidade = int(quantidade_entry.get())
            preco = float(preco_str)
            if quantidade < 0 or preco < 0:
                messagebox.showerror("Erro", "Quantidade/Preço não podem ser negativos.")
                return
            editar_produto(idp, nome, preco, quantidade, codigo_barras)
            exibir_lista_produtos(treeview)
            messagebox.showinfo("Sucesso", "Produto atualizado.")
            _limpar_campos_estoque() 
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao atualizar produto: {e}")

    def carregar_produto(event):
        sel = treeview.selection()
        if not sel:
            return
        vals = treeview.item(sel[0], "values")
        
        limpar_campos(nome_entry, preco_entry, quantidade_entry, codigo_barras_entry, 
                    id_produto_remover_entry, quantidade_remover_entry, 
                    id_produto_imprimir_entry, quantidade_impressao_entry)

        nome_entry.insert(0, vals[1])
        preco_limpo = vals[2].replace('R$', '').strip().replace(',', '.')
        preco_entry.insert(0, preco_limpo)    
        
        quantidade_entry.insert(0, vals[3]) 
    
        codigo_barras_entry.insert(0, vals[4])
        
        id_produto_remover_entry.insert(0, vals[0])
        id_produto_imprimir_entry.insert(0, vals[0])
    
    def remover_produto_btn():
        id_str = id_produto_remover_entry.get().strip()
        qt_str = quantidade_remover_entry.get().strip()
    
        if not id_str or not qt_str:
            messagebox.showerror("Erro", "ID e Quantidade obrigatórios.")
            return
        if not id_str.isdigit() or not qt_str.isdigit():
            messagebox.showerror("Erro", "ID e Quantidade devem ser números inteiros.")
            return
        idp = int(id_str); qt = int(qt_str)
        if idp <= 0 or qt <= 0:
            messagebox.showerror("Erro", "Valores positivos necessários.")
            return
        remover_produto(idp, qt)
        exibir_lista_produtos(treeview)

   
    def imprimir_produto_btn():
        id_str = id_produto_imprimir_entry.get().strip()
        qt_impressao_str = quantidade_impressao_entry.get().strip()
        if not id_str or not qt_impressao_str:
            messagebox.showerror("Erro", "ID e Quantidade para impressão obrigatórios.")
            return
        if not id_str.isdigit() or not qt_impressao_str.isdigit():
            messagebox.showerror("Erro", "Campos devem ser inteiros.")
            return
        idp = int(id_str); qt = int(qt_impressao_str)
        if idp <= 0 or qt <= 0:
            messagebox.showerror("Erro", "Valores devem ser positivos.")
            return
        if qt > 999:
            messagebox.showwarning("Atenção", "Quantidade muito alta (máx sugerido 999).")
        gerar_etiqueta(idp, qt, tipo=codigo_tipo.get())

    def buscar_em_tempo_real(event=None):
        termo = busca_entry.get().strip()
        exibir_lista_produtos(treeview, termo)
        
    # --- Função de Manipulação de Teclado (Scanner) ---
    
    def manipular_entrada_teclado(event):
        nonlocal codigo_barras_sendo_lido, ultimo_timestamp 
        agora = time.time()
        foco = root.focus_get()
        
        # Se a aba Venda estiver ativa (Caixa Registradora)
        if notebook.tab(notebook.select(), "text") == "Venda":
            
            campos_foco_venda = [quantidade_caixa_entry]
            
            # Se o foco estiver no campo Quantidade e for Enter, não bloqueia
            if foco in campos_foco_venda:
                if event.keysym == "Return":
                    # Força a leitura do produto no campo de código, se estiver preenchido
                    if codigo_caixa_entry.get().strip():
                        ler_produto_venda()
                    return 

            # Lógica de simulação de scanner
            if event.keysym == "Return":
                if codigo_barras_sendo_lido and codigo_barras_sendo_lido.isdigit():
                    
                    # Insere o código lido no campo de código de barras da venda
                    codigo_caixa_entry.delete(0, tk.END)
                    codigo_caixa_entry.insert(0, codigo_barras_sendo_lido)
                    
                    # Tenta processar o item
                    ler_produto_venda()
                    
                    # Reseta o scanner buffer
                    codigo_barras_sendo_lido = ""
                    ultimo_timestamp = 0
                    
                    # Bloqueia a propagação do evento Enter para evitar chamadas duplas
                    return "break" 
            
            # Limpa o buffer se o tempo limite for excedido
            if agora - ultimo_timestamp > INTERVALO_MAXIMO_LEITURA:
                codigo_barras_sendo_lido = ""
                
            # Adiciona o dígito ao buffer
            if hasattr(event, "char") and event.char.isdigit():
                codigo_barras_sendo_lido += event.char
                ultimo_timestamp = agora
                return "break" # Consome o evento
                
            # Limpa o buffer se um caractere não-dígito for pressionado entre dígitos
            if codigo_barras_sendo_lido and (not hasattr(event, "char") or not event.char.isdigit()) and event.keysym != "Return":
                codigo_barras_sendo_lido = ""
                ultimo_timestamp = 0
                
            # Se o buffer não for ativado, permite o processamento normal (ex: Backspace, setas)
            return
                
        # Se a aba Estoque estiver ativa
        else:           
            # Se a leitura lenta ocorrer aqui, ela limpa o buffer
            if agora - ultimo_timestamp > INTERVALO_MAXIMO_LEITURA:
                codigo_barras_sendo_lido = ""
            if event.keysym == "Return":
                codigo_barras_sendo_lido = "" # Limpa ao apertar enter
            
            return # Permite o comportamento padrão
    
    # --- Configuração Principal da Janela ---
    criar_banco()
    
    # Notebook (Abas)
    notebook = ttk.Notebook(root)
    notebook.pack(pady=10, padx=10, expand=True, fill="both")

    # --- Aba Estoque (Inventário) ---
    aba_estoque = ttk.Frame(notebook)
    notebook.add(aba_estoque, text='Estoque')
    
    # Estrutura de dois painéis (Controles e Lista)
    painel_estoque = tk.Frame(aba_estoque)
    painel_estoque.pack(fill="both", expand=True, padx=5, pady=5)
    
    controles_estoque_frame = tk.Frame(painel_estoque, relief=tk.GROOVE, bd=1)
    controles_estoque_frame.pack(side="top", fill="x", padx=5, pady=5)
    
    lista_estoque_frame = tk.Frame(painel_estoque)
    lista_estoque_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    
    
    # --- Controles de Cadastro/Edição (Top Section) ---
    cadastro_frame = tk.LabelFrame(controles_estoque_frame, text="✅ Cadastro e Edição de Produto")
    cadastro_frame.pack(fill="x", padx=10, pady=5)
    
    # Campos
    campos_frame = tk.Frame(cadastro_frame)
    campos_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(campos_frame, text="Nome:").pack(side="left", padx=(5, 2))
    nome_entry = tk.Entry(campos_frame, width=30)
    nome_entry.pack(side="left", padx=5)
    
    tk.Label(campos_frame, text="Preço (R$):").pack(side="left", padx=2)
    preco_entry = tk.Entry(campos_frame, width=10)
    preco_entry.pack(side="left", padx=5)
    
    tk.Label(campos_frame, text="Quantidade:").pack(side="left", padx=2)
    quantidade_entry = tk.Entry(campos_frame, width=10)
    quantidade_entry.insert(0, "0")
    quantidade_entry.pack(side="left", padx=5)
    
    tk.Label(campos_frame, text="Cód. Barras/QR:").pack(side="left", padx=2)
    codigo_barras_entry = tk.Entry(campos_frame, width=15)
    codigo_barras_entry.pack(side="left", padx=5)
    
    # Botões
    botoes_cadastro_frame = tk.Frame(cadastro_frame)
    botoes_cadastro_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Button(botoes_cadastro_frame, text="➕ Adicionar/Entrada", bg="#04AA6D", fg="white", command=adicionar_produto_btn).pack(side="left", padx=5)
    tk.Button(botoes_cadastro_frame, text="✏️ Editar Selecionado", bg="#3498DB", fg="white", command=editar_produto_btn).pack(side="left", padx=5)
    tk.Button(botoes_cadastro_frame, text="🧹 Limpar Campos", command=lambda: limpar_campos(nome_entry, preco_entry, quantidade_entry, codigo_barras_entry, id_produto_remover_entry, quantidade_remover_entry, id_produto_imprimir_entry, quantidade_impressao_entry)).pack(side="left", padx=5)
    
    
    # --- Controles de Movimentação e Etiquetas (Bottom Section) ---
    movimento_frame = tk.LabelFrame(controles_estoque_frame, text="📦 Movimentação, Busca e Etiquetas")
    movimento_frame.pack(fill="x", padx=10, pady=5)
    
    # Frame de Busca
    busca_frame = tk.Frame(movimento_frame)
    busca_frame.pack(fill="x", padx=5, pady=5)
    tk.Label(busca_frame, text="🔎 Buscar (Nome/Cód.):").pack(side="left", padx=(5, 2))
    busca_entry = tk.Entry(busca_frame, width=40)
    busca_entry.pack(side="left", padx=5)
    busca_entry.bind('<KeyRelease>', buscar_em_tempo_real)

    # Frame de Saída de Estoque
    saida_frame = tk.LabelFrame(movimento_frame, text="➖ Baixa/Saída de Estoque")
    saida_frame.pack(side="left", padx=10, pady=5)
    
    tk.Label(saida_frame, text="ID:").pack(side="left", padx=2)
    id_produto_remover_entry = tk.Entry(saida_frame, width=5)
    id_produto_remover_entry.pack(side="left", padx=5)
    
    tk.Label(saida_frame, text="Qtde:").pack(side="left", padx=2)
    quantidade_remover_entry = tk.Entry(saida_frame, width=5)
    quantidade_remover_entry.insert(0, "1")
    quantidade_remover_entry.pack(side="left", padx=5)
    
    tk.Button(saida_frame, text="⬇️ Remover Estoque", bg="#E74C3C", fg="white", command=remover_produto_btn).pack(side="left", padx=5)
    
    # Frame de Etiquetas
    frame_etiqueta = tk.LabelFrame(movimento_frame, text="🏷️ Gerar Etiquetas PDF")
    frame_etiqueta.pack(side="left", padx=10, pady=5)
    
    tk.Label(frame_etiqueta, text="ID:").pack(side="left", padx=2)
    id_produto_imprimir_entry = tk.Entry(frame_etiqueta, width=5)
    id_produto_imprimir_entry.pack(side="left", padx=5)
    
    tk.Label(frame_etiqueta, text="Qtde Imp.:").pack(side="left", padx=2)
    quantidade_impressao_entry = tk.Entry(frame_etiqueta, width=5)
    quantidade_impressao_entry.insert(0, "10")
    quantidade_impressao_entry.pack(side="left", padx=5)

    # --- RADIOBUTTONS DE TIPO DE CÓDIGO ---
    frame_radio_tipo = tk.Frame(frame_etiqueta)
    frame_radio_tipo.pack(side="left", padx=5, expand=True, fill="x")
    
    tk.Label(frame_radio_tipo, text="Tipo:").pack(side="left", padx=(0, 2))
    
    # Opção 1: Code 128 (padrão)
    tk.Radiobutton(frame_radio_tipo, 
                    text="Code 128", 
                    variable=codigo_tipo, 
                    value="code128").pack(side="left", padx=5)

    # Opção 2: QR Code
    tk.Radiobutton(frame_radio_tipo, 
                    text="QR Code", 
                    variable=codigo_tipo, 
                    value="qrcode").pack(side="left", padx=5)

    # Opção 3: EAN 13
    tk.Radiobutton(frame_radio_tipo, 
                    text="EAN 13", 
                    variable=codigo_tipo, 
                    value="ean13").pack(side="left", padx=5)
                    
    tk.Button(frame_etiqueta, text="🖨️ Gerar PDF", bg="#2ECC71", fg="white", 
              command=gerar_etiqueta_btn_interna).pack(side="left", padx=(5, 0))


    # --- Lista (Treeview) de Produtos ---
    cols = ("id", "nome", "preco", "quantidade", "codigo_barras")
    treeview = ttk.Treeview(lista_estoque_frame, columns=cols, show='headings')

    treeview.heading("id", text="ID", command=lambda: ordenar_lista(treeview, 'id'))
    treeview.heading("nome", text="Nome", command=lambda: ordenar_lista(treeview, 'nome'))
    treeview.heading("preco", text="Preço", command=lambda: ordenar_lista(treeview, 'preco'))
    treeview.heading("quantidade", text="Estoque", command=lambda: ordenar_lista(treeview, 'quantidade'))
    treeview.heading("codigo_barras", text="Cód. Barras/QR", command=lambda: ordenar_lista(treeview, 'codigo_barras'))

    treeview.column("id", width=40, stretch=tk.NO, anchor='center')
    treeview.column("nome", width=650, stretch=tk.YES, anchor='center') # Nome estica e alinha à esquerda
    treeview.column("preco", width=100, stretch=tk.NO, anchor='center') # Preço alinha à direita
    treeview.column("quantidade", width=80, stretch=tk.NO, anchor='center')
    treeview.column("codigo_barras", width=150, stretch=tk.NO, anchor='center')

    # ✅ BLOQUEIA APENAS O ARRASTO DAS COLUNAS, mas permite o clique e a ordenação.
    treeview.bind('<B1-Motion>', lambda e: 'break') 

    treeview.pack(fill="both", expand=True)

    # 🖱️ Permite o clique duplo (carregar inputs)
    treeview.bind('<Double-1>', carregar_produto)

    # 🖱️ Permite o clique simples (selecionar item, que dispara carregar_produto)
    treeview.bind('<<TreeviewSelect>>', carregar_produto)

    # Scrollbar
    scrollbar = ttk.Scrollbar(lista_estoque_frame, orient="vertical", command=treeview.yview)
    treeview.configure(yscrollcommand=scrollbar.set)

    treeview.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Carregar dados iniciais
    exibir_lista_produtos(treeview)
    
    # Cria o frame de rodapé
    footer_frame = tk.Frame(root, pady=5) 
    footer_frame.pack(side="bottom", fill="x")
    
    # Botões do Rodapé
    
    # --- NOVO BOTÃO: RELATÓRIO DE ESTOQUE COMPLETO ---
    btn_relatorio_estoque = tk.Button(
        botao_relatorio_frame,
        text="📄 ESTOQUE ATUAL",
        bg="#04AA6D",
        fg="white",
        font=("Helvetica", 10, "bold"),
        command=gerar_relatorio_estoque
        )
    btn_relatorio_estoque.pack(anchor="e")
    
    # --- Aba Venda (Caixa Registradora) ---
    aba_venda = ttk.Frame(notebook)
    notebook.add(aba_venda, text='Venda')
    
    # Estrutura de Venda: (Lado Esquerdo: Lista | Lado Direito: Controles)
    painel_venda = tk.Frame(aba_venda)
    painel_venda.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Frame da Lista de Venda (Left Side)
    lista_venda_frame = tk.Frame(painel_venda)
    lista_venda_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
    
    # Treeview da Venda
    cols_venda = ("nome", "preco", "quantidade", "subtotal", "codigo_barras")
    treeview_venda = ttk.Treeview(lista_venda_frame, columns=cols_venda, show='headings')

    treeview_venda.heading("nome", text="Produto")
    treeview_venda.heading("preco", text="Preço Unit.")
    treeview_venda.heading("quantidade", text="Qtde")
    treeview_venda.heading("subtotal", text="Subtotal")
    treeview_venda.heading("codigo_barras", text="Cód.") # Coluna oculta ou estreita

    # Apenas a coluna "nome" estica
    treeview_venda.column("nome", width=250, stretch=tk.YES, anchor='center')

    # Todas as outras com tamanho fixo
    treeview_venda.column("preco", width=100, stretch=tk.NO, anchor='center')
    treeview_venda.column("quantidade", width=50, stretch=tk.NO, anchor='center')
    treeview_venda.column("subtotal", width=100, stretch=tk.NO, anchor='center')
    treeview_venda.column("codigo_barras", width=0, stretch=tk.NO) # Coluna oculta para pegar o código

    # Impede redimensionamento de qualquer coluna
    def bloquear_resize_venda(event):
        if treeview_venda.identify_region(event.x, event.y) == "separator":
            return "break"

    treeview_venda.bind("<Button-1>", bloquear_resize_venda)

    # Ocupa 100% do frame
    treeview_venda.pack(fill="both", expand=True)
    
    # Scrollbar para a lista de venda
    scrollbar_venda = ttk.Scrollbar(lista_venda_frame, orient="vertical", command=treeview_venda.yview)
    treeview_venda.configure(yscrollcommand=scrollbar_venda.set)
    
    treeview_venda.pack(side="top", fill="both", expand=True)
    scrollbar_venda.pack(side="right", fill="y")
    
    # Total Label (Bottom of List Frame)
    total_label = tk.Label(lista_venda_frame, text="TOTAL: R$ 0,00", font=('Arial', 24, 'bold'), fg="#2C3E50")
    total_label.pack(side="bottom", fill="x", pady=10)
    
    
    # Frame de Controles de Venda (Right Side)
    controles_venda_frame = tk.Frame(painel_venda, width=300)
    controles_venda_frame.pack(side="right", fill="y", padx=5)
    controles_venda_frame.pack_propagate(False) # Impede o frame de encolher

    # Título
    tk.Label(controles_venda_frame, text="🛒 CAIXA REGISTRADORA", font=('Arial', 14, 'bold'), pady=10).pack(fill="x")
    
    # Entrada de Código e Quantidade
    entrada_venda_frame = tk.LabelFrame(controles_venda_frame, text="Leitura/Entrada")
    entrada_venda_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(entrada_venda_frame, text="Cód. (Scanner):").pack(fill="x", padx=5, pady=(5, 0))
    codigo_caixa_entry = tk.Entry(entrada_venda_frame, font=('Arial', 12))
    codigo_caixa_entry.pack(fill="x", padx=5)
    codigo_caixa_entry.focus_set() # Define o foco inicial
    
    qt_frame = tk.Frame(entrada_venda_frame)
    qt_frame.pack(fill="x", padx=5, pady=5)
    tk.Label(qt_frame, text="Qtde:").pack(side="left", padx=5)
    quantidade_caixa_entry = tk.Entry(qt_frame, width=10)
    quantidade_caixa_entry.insert(0, "1")
    quantidade_caixa_entry.pack(side="left", padx=5)
    
    # Botão para adicionar manualmente (Enter key deve ser usado pelo scanner)
    tk.Button(qt_frame, text="➕ Adicionar Item", bg="#04AA6D", fg="white", command=ler_produto_venda).pack(side="right")
    
    # Status da última leitura
    status_venda_label = tk.Label(entrada_venda_frame, text="Pronto para ler o código.", fg="#34495E")
    status_venda_label.pack(fill="x", pady=(5, 10))
    
    # Controles de Pagamento e Finalização
    pagamento_frame = tk.LabelFrame(controles_venda_frame, text="Pagamento e Finalização")
    pagamento_frame.pack(fill="x", padx=5, pady=10)
    
    tk.Label(pagamento_frame, text="Valor Recebido (R$):").pack(fill="x", padx=5, pady=(5, 0))
    valor_recebido_entry = tk.Entry(pagamento_frame, font=('Arial', 12))
    valor_recebido_entry.pack(fill="x", padx=5)
    valor_recebido_entry.bind('<KeyRelease>', lambda e: calcular_troco()) # Calcula o troco em tempo real
    
    troco_label = tk.Label(pagamento_frame, text="✅ Troco: R$ 0,00", font=('Arial', 12, 'bold'), fg="#04AA6D", pady=5)
    troco_label.pack(fill="x", pady=5)
    
    tk.Button(pagamento_frame, text="💵 FINALIZAR VENDA", bg="#2980B9", fg="white", 
              font=('Arial', 12, 'bold'), command=finalizar_venda).pack(fill="x", padx=5, pady=(5, 10))
    
    tk.Button(controles_venda_frame, text="❌ Remover Item Selecionado", bg="#E74C3C", fg="white", 
              command=remover_item_venda).pack(fill="x", padx=5, pady=(5, 10))
              
    tk.Button(controles_venda_frame, text="🗑️ Cancelar Venda (Limpar Lista)", 
              command=lambda: (venda_atual.clear(), atualizar_lista_venda(), status_venda_label.config(text="Venda cancelada."))) \
              .pack(fill="x", padx=5, pady=5)
              
    
    # --- Menu Principal ---
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    menu_ajuda = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Ajuda", menu=menu_ajuda)
    menu_ajuda.add_command(label="Contato do Desenvolvedor", command=lambda: mostrar_contato(root))
    menu_ajuda.add_separator()
    menu_ajuda.add_command(label="Sair", command=root.quit)
    
    # --- Configuração do Scanner Global ---
    root.bind('<Key>', manipular_entrada_teclado)
    
    root.mainloop()

# --- Execução do Programa ---
if __name__ == "__main__":
    interface()