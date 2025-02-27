import sqlite3
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import barcode
from barcode.writer import ImageWriter
import os

def criar_banco():
    conexao = sqlite3.connect('estoque.db')
    cursor = conexao.cursor()

    # Criando a tabela de produtos
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        codigo_barras TEXT NOT NULL
    )
    ''')

    # Commit e fechamento da conexão
    conexao.commit()
    conexao.close()

def interface():
    global root
    root = tk.Tk()
    root.title("Controle de Estoque - Criado por: Paulo Neto")
    root.geometry("1235x700")  # Ajustado para o tamanho da janela
    
    # Bloquear o redimensionamento da janela
    root.resizable(False, False)  # False para largura e altura

    # Imagem do carrinho de compras no canto superior direito
    imagem_carrinho_pil = Image.open("img/carrinho.png")
    imagem_carrinho_pil_resized = imagem_carrinho_pil.resize((150, 150))
    imagem_carrinho = ImageTk.PhotoImage(imagem_carrinho_pil_resized)

    imagem_label = tk.Label(root, image=imagem_carrinho)
    imagem_label.grid(row=0, column=0, padx=10, pady=10)
    
    # Título e Subtítulo
    titulo = tk.Label(root, text="Supermercado ABC", font=("Helvetica", 16, "bold"))
    titulo.grid(row=0, column=1, padx=10, pady=10, sticky="w")
    
    # Botão para excluir todos os dados e reiniciar os IDs
    excluir_button = tk.Button(root, text="Excluir Banco de Dados", bg="#e02835", fg="white", command=lambda: excluir_todos_dados(treeview))
    excluir_button.grid(row=20, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
    
    # Entradas para dados do produto
    tk.Label(root, text="Nome do Produto").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    nome_entry = tk.Entry(root, width=33)
    nome_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    tk.Label(root, text="Quantidade").grid(row=3, column=0, padx=10, pady=5, sticky="w")
    quantidade_entry = tk.Entry(root, width=33)
    quantidade_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")

    tk.Label(root, text="Código de Barras").grid(row=4, column=0, padx=10, pady=5, sticky="w")
    codigo_barras_entry = tk.Entry(root, width=33)
    codigo_barras_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
    
    # Exemplo de como pegar o número do código de barras de um campo de entrada (Entry)
    numero_produto_entry = tk.Entry(root)
    numero_produto_entry.get()  # Pegando o valor inserido no campo de entrada

    # Treeview para exibir a lista de produtos
    treeview = ttk.Treeview(root, columns=("ID", "Nome", "Código de Barras", "Quantidade"), show="headings")
    treeview.grid(row=1, column=2, rowspan=20, padx=10, pady=10, sticky="nsew")

    treeview.heading("ID", text="ID", command=lambda: ordenar_lista(treeview, "id"))
    treeview.heading("Nome", text="Nome", command=lambda: ordenar_lista(treeview, "nome"))
    treeview.heading("Código de Barras", text="Código de Barras", command=lambda: ordenar_lista(treeview, "codigo_barras"))
    treeview.heading("Quantidade", text="Quantidade", command=lambda: ordenar_lista(treeview, "quantidade"))

    # Estado de ordenação
    ordenar_id_ascendente = True
    ordenar_nome_ascendente = True
    ordenar_codigo_barras_ascendente = True
    ordenar_quantidade_ascendente = True

    def ordenar_lista(treeview, coluna):
        nonlocal ordenar_id_ascendente, ordenar_nome_ascendente, ordenar_codigo_barras_ascendente, ordenar_quantidade_ascendente

        if coluna == "id":
            ordem = ordenar_id_ascendente
            ordenar_id_ascendente = not ordenar_id_ascendente
            query = "ORDER BY id " + ("ASC" if ordem else "DESC")
        elif coluna == "nome":
            ordem = ordenar_nome_ascendente
            ordenar_nome_ascendente = not ordenar_nome_ascendente
            query = "ORDER BY nome " + ("ASC" if ordem else "DESC")
        elif coluna == "codigo_barras":
            ordem = ordenar_codigo_barras_ascendente
            ordenar_codigo_barras_ascendente = not ordenar_codigo_barras_ascendente
            query = "ORDER BY codigo_barras " + ("ASC" if ordem else "DESC")
        else:
            ordem = ordenar_quantidade_ascendente
            ordenar_quantidade_ascendente = not ordenar_quantidade_ascendente
            query = "ORDER BY quantidade " + ("ASC" if ordem else "DESC")

        conexao = sqlite3.connect('estoque.db')
        cursor = conexao.cursor()
        cursor.execute(f"SELECT id, nome, codigo_barras, quantidade FROM produtos {query}")
        produtos = cursor.fetchall()
        conexao.close()

        # Limpar a Treeview antes de adicionar os novos itens
        for item in treeview.get_children():
            treeview.delete(item)

        # Inserir os produtos na Treeview
        for produto in produtos:
            treeview.insert('', 'end', values=produto)

    # Função para adicionar produto
    def adicionar_produto_btn():
        nome = nome_entry.get()
        try:
            quantidade = int(quantidade_entry.get())
            codigo_barras = codigo_barras_entry.get()

            # Verificando se os campos obrigatórios estão preenchidos
            if not nome or not codigo_barras or quantidade <= 0:
                messagebox.showerror("Erro", "Os campos Nome, Quantidade e Código de Barras são obrigatórios.")
                return

            adicionar_produto(nome, quantidade, codigo_barras)
            messagebox.showinfo("Sucesso", "Produto adicionado com sucesso!")
            exibir_lista_produtos(treeview)  # Atualizar a lista de produtos
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira um valor numérico válido para a quantidade.")

    def remover_produto_btn():
        try:
            # Obtém o ID e a quantidade a ser removida
            id_produto = int(id_produto_remover_entry.get())
            quantidade_remover = int(quantidade_remover_entry.get())
            
            # Chama a função para remover o produto, passando o ID e a quantidade
            remover_produto(id_produto, quantidade_remover)
                       
            # Atualiza a lista de produtos na interface após a remoção
            exibir_lista_produtos(treeview)  # Chama a função para atualizar a Treeview com a nova lista
                
        except ValueError:
            # Exibe um erro se o valor de ID ou quantidade não for numérico
            messagebox.showerror("Erro", "Por favor, insira um valor numérico válido para o ID e a quantidade.")

    # Função para editar produto
    def editar_produto_btn():
        try:
            nome = nome_entry.get()
            try:
                quantidade = int(quantidade_entry.get())
                codigo_barras = codigo_barras_entry.get()

                # Verificando se os campos obrigatórios estão preenchidos
                if not nome or not codigo_barras or quantidade <= 0:
                    messagebox.showerror("Erro", "Os campos Nome, Quantidade e Código de Barras são obrigatórios.")
                    return
                
                # Verifica se o id do produto foi carregado antes de editar
                if 'id_produto_edit' in globals():
                    id_produto = id_produto_edit
                    
                    editar_produto(nome, quantidade, codigo_barras)  # Chama a função de editar produto
                
                    exibir_lista_produtos(treeview)  # Atualiza a lista de produtos
                else:
                    messagebox.showerror("Erro", "Nenhum produto selecionado para editar.")

                #  editar_produto(id_produto, nome, quantidade, codigo_barras)
                #  messagebox.showinfo("Sucesso", "Produto editado com sucesso!")
                #  exibir_lista_produtos(treeview)  # Atualizar a lista de produtos
        
            except ValueError:
                messagebox.showerror("Erro", "Por favor, insira um valor válido para a quantidade.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao editar o produto: {e}")

    # Função para capturar o duplo clique na Treeview e carregar os dados nos campos de entrada
    def carregar_produto(event):
        # Obtém o item selecionado da Treeview
        item_selecionado = treeview.selection()
        if item_selecionado:
            # Pega os valores da linha selecionada
            produto = treeview.item(item_selecionado, 'values')
            
            # Carrega as informações nos campos de entrada
            id_produto = produto[0]
            nome_entry.delete(0, tk.END)
            nome_entry.insert(0, produto[1])
            
            quantidade_entry.delete(0, tk.END)
            quantidade_entry.insert(0, produto[3])
            
            codigo_barras_entry.delete(0, tk.END)
            codigo_barras_entry.insert(0, produto[2])
            
            # Opcional: você pode armazenar o id do produto para edições ou remoções futuras
            global id_produto_edit
            id_produto_edit = id_produto

    # Adicionar o evento de duplo clique na Treeview
    treeview.bind("<Double-1>", carregar_produto)

    # Função para imprimir o produto
    def imprimir_produto_btn():
        try:
            id_produto = int(id_produto_imprimir_entry.get())
            quantidade_impressao = int(quantidade_impressao_entry.get())
            if quantidade_impressao <= 0:
                messagebox.showerror("Erro", "A quantidade de impressões deve ser maior que 0.")
                return
            gerar_etiqueta(id_produto, quantidade_impressao)
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira valores válidos para o ID e a quantidade de impressões.")

    # Entradas para remoção de produto
    tk.Label(root, text="ID do Produto para Remover").grid(row=9, column=0, padx=10, pady=5, sticky="w")
    id_produto_remover_entry = tk.Entry(root, width=33)
    id_produto_remover_entry.grid(row=9, column=1, padx=10, pady=5, sticky="w")

    tk.Label(root, text="Quantidade a Remover").grid(row=10, column=0, padx=10, pady=5, sticky="w")
    quantidade_remover_entry = tk.Entry(root, width=33)
    quantidade_remover_entry.grid(row=10, column=1, padx=10, pady=5, sticky="w")

    remover_button = tk.Button(root, text="Remover Produto", bg="#043640", fg="white", command=remover_produto_btn)
    remover_button.grid(row=11, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # Entradas para impressão do produto
    tk.Label(root, text="ID do Produto para Impressão").grid(row=12, column=0, padx=10, pady=5, sticky="w")
    id_produto_imprimir_entry = tk.Entry(root, width=33)
    id_produto_imprimir_entry.grid(row=12, column=1, padx=10, pady=5, sticky="w")

    tk.Label(root, text="Quantidade de Impressões").grid(row=13, column=0, padx=10, pady=5, sticky="w")
    quantidade_impressao_entry = tk.Entry(root, width=33)
    quantidade_impressao_entry.grid(row=13, column=1, padx=10, pady=5, sticky="w")

    imprimir_button = tk.Button(root, text="Imprimir Produto", bg="#2e8ad1", fg="white", command=imprimir_produto_btn)
    imprimir_button.grid(row=14, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # Botões "Adicionar", "Editar"
    adicionar_button = tk.Button(root, text="Adicionar Produto", bg="#043640", fg="white", command=adicionar_produto_btn)
    adicionar_button.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

    editar_button = tk.Button(root, text="Editar Produto", bg="#043640", fg="white", command=editar_produto_btn)
    editar_button.grid(row=5, column=1, padx=10, pady=10, sticky="ew")

    # Exibir a lista de produtos inicialmente
    exibir_lista_produtos(treeview)

    root.mainloop()

def excluir_todos_dados(treeview):
    # Confirmação antes de excluir todos os dados
    resposta = messagebox.askyesno("Confirmação", "Você tem certeza que deseja excluir TODOS os dados do banco?")
    
    if resposta:  # Se o usuário confirmar
        try:
            # Conexão com o banco de dados
            conexao = sqlite3.connect('estoque.db')
            cursor = conexao.cursor()

            # Apagar todos os dados da tabela
            cursor.execute("DELETE FROM produtos")
            conexao.commit()

            # Reiniciar o contador de IDs (resetando a sequência)
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='produtos'")
            conexao.commit()

            # Fechar a conexão
            conexao.close()

            # Exibir uma mensagem de sucesso
            messagebox.showinfo("Sucesso", "Todos os dados foram excluídos com sucesso!")

            # Atualiza a lista de produtos na interface após a exclusão
            exibir_lista_produtos(treeview)  # Chama a função para atualizar a Treeview com a nova lista
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")



def adicionar_produto(nome, quantidade, codigo_barras):
    conexao = sqlite3.connect('estoque.db')
    cursor = conexao.cursor()

    # Verificando se o produto já existe no banco de dados
    cursor.execute("SELECT id, quantidade FROM produtos WHERE nome = ? AND codigo_barras = ?", (nome, codigo_barras))
    produto_existente = cursor.fetchone()

    if produto_existente:
        # Produto existe, acumulando a quantidade
        id_produto = produto_existente[0]
        quantidade_atual = produto_existente[1]
        nova_quantidade = quantidade_atual + quantidade
        cursor.execute("UPDATE produtos SET quantidade = ? WHERE id = ?", (nova_quantidade, id_produto))
    else:
        # Produto não existe, adicionando um novo produto
        cursor.execute("INSERT INTO produtos (nome, quantidade, codigo_barras) VALUES (?, ?, ?)",
                       (nome, quantidade, codigo_barras))

    conexao.commit()
    conexao.close()

def remover_produto(id_produto, quantidade_remover):
    conexao = sqlite3.connect('estoque.db')
    cursor = conexao.cursor()

    # Verificando a quantidade do produto no estoque
    cursor.execute("SELECT quantidade FROM produtos WHERE id = ?", (id_produto,))
    produto = cursor.fetchone()

    if produto is None:
        print(f"Produto com ID {id_produto} não encontrado.")  # Depuração
        messagebox.showerror("Erro", "Produto não encontrado!")
        conexao.close()
        return

    quantidade_estoque = produto[0]

    if quantidade_remover > quantidade_estoque:
        messagebox.showerror("Erro", "Quantidade a ser removida é maior do que o estoque disponível!")
    else:
        # Atualizando a quantidade do produto após a remoção
        nova_quantidade = quantidade_estoque - quantidade_remover
        cursor.execute("UPDATE produtos SET quantidade = ? WHERE id = ?", (nova_quantidade, id_produto))

        # Se a quantidade for 0, o produto será removido
        if nova_quantidade == 0:
            cursor.execute("DELETE FROM produtos WHERE id = ?", (id_produto,))
            print(f"Produto com ID {id_produto} foi removido do estoque.")  # Depuração
            
        # Exibe uma mensagem de sucesso
        messagebox.showinfo("Sucesso", "Produto removido com sucesso!")

        conexao.commit()
        conexao.close()

def editar_produto(nome, quantidade, codigo_barras):
    try:
        conexao = sqlite3.connect('estoque.db')
        cursor = conexao.cursor()
        
        # Executa a atualização
        cursor.execute("UPDATE produtos SET nome = ?, quantidade = ?, codigo_barras = ? WHERE codigo_barras = ?",
                    (nome, quantidade, codigo_barras, codigo_barras))
        
        # Verifica quantas linhas foram afetadas
        if cursor.rowcount == 0:
            messagebox.showerror("Erro", "Produto não encontrado ou nenhuma alteração realizada.")
        else:
            conexao.commit()
            messagebox.showinfo("Sucesso", "Produto atualizado com sucesso!")
            
    except sqlite3.Error as e:
        messagebox.showerror("Erro", f"Erro ao acessar o banco de dados: {e}")
    
    finally:
        conexao.close()

def exibir_lista_produtos(treeview, ordenar_id_ascendente=True):
    conexao = sqlite3.connect('estoque.db')
    cursor = conexao.cursor()

    cursor.execute("SELECT id, nome, codigo_barras, quantidade FROM produtos ORDER BY nome")
    produtos = cursor.fetchall()

    # Limpar a Treeview antes de adicionar os novos itens
    for item in treeview.get_children():
        treeview.delete(item)

    # Inserir os produtos na Treeview
    for produto in produtos:
        treeview.insert('', 'end', values=produto)

    conexao.close()

def gerar_etiqueta(id_produto, quantidade_impressao):
    conexao = sqlite3.connect('estoque.db')
    cursor = conexao.cursor()
    cursor.execute("SELECT nome, codigo_barras, quantidade FROM produtos WHERE id = ?", (id_produto,))
    produto = cursor.fetchone()
    conexao.close()

    if produto:
        nome, codigo_barras, quantidade = produto

        # Verifica se as pastas necessárias existem, se não, cria
        pasta = 'C:/_Etiquetas-controle de estoque'
        pasta_imagens = f'{pasta}/etiquetas_png'
        pasta_pdfs = f'{pasta}/etiquetas_pdf'

        # Garantir que as pastas 'etiquetas_png' e 'etiquetas_pdf' existam
        if not os.path.exists(pasta_imagens):
            os.makedirs(pasta_imagens)

        if not os.path.exists(pasta_pdfs):
            os.makedirs(pasta_pdfs)

        # Gerando código de barras com Code128
        barcode_code = barcode.get_barcode_class('code128') 
        barcode_instance = barcode_code(codigo_barras, writer=ImageWriter())

        # Caminho para salvar o código de barras como imagem PNG, removendo o ".png" extra
        caminho_imagem = f'{pasta_imagens}/codigo_de_barras_id-{id_produto}'

        try:
            barcode_instance.save(caminho_imagem)

            # Verifica se o arquivo foi criado corretamente antes de usar
            if not os.path.exists(f"{caminho_imagem}.png"):
                messagebox.showerror("Erro", "Erro ao salvar a imagem do código de barras.")
                return
          
        except Exception as e:
            print(f"Erro ao salvar o código de barras: {e}")
            messagebox.showerror("Erro", f"Erro ao salvar o código de barras: {e}")
            return

        # Gerar o PDF com todas as etiquetas em um único arquivo
        caminho_pdf = f'{pasta_pdfs}/etiquetas_id-{id_produto}.pdf'
        
        try:
            c = canvas.Canvas(caminho_pdf, pagesize=letter)

            # Definindo as margens para as etiquetas
            margem_topo = 750
            espacamento_vertical = 200  # Espaçamento vertical entre as etiquetas
            espacamento_horizontal = 250  # Espaçamento horizontal entre as etiquetas

            # Definindo a posição inicial
            x_position = 50  # Posição inicial na horizontal
            y_position = margem_topo  # Posição inicial na vertical

            for i in range(quantidade_impressao):
                # Desenhando a etiqueta com o texto
                c.setFont("Helvetica-Bold", 16)
                c.drawString(x_position, y_position, f"Produto: {nome}")
                c.setFont("Helvetica", 12)
                c.drawString(x_position, y_position - 20, f"Etiqueta {i+1}/{quantidade_impressao}")
                c.drawString(x_position, y_position - 40, f"Código de Barras: {codigo_barras}")

                # Desenhando a imagem do código de barras abaixo do texto
                c.drawImage(f"{caminho_imagem}.png", x_position + 0, y_position - 150, width=100, height=100)

                # Calculando a posição para a próxima etiqueta
                if (i + 1) % 2 == 0:
                    # Se for a segunda coluna, muda para a próxima linha
                    x_position = 50
                    y_position -= espacamento_vertical
                else:
                    # Caso contrário, continua na primeira coluna
                    x_position = 300

                # Checando se a página precisa ser virada
                if (i + 1) % 8 == 0:  # Quando atingir 8 etiquetas, vira a página
                    c.showPage()
                    # Resetando a posição para a primeira etiqueta da nova página
                    x_position = 50
                    y_position = margem_topo

            # Salva o arquivo PDF
            c.save()

            # Verifica se o PDF foi gerado corretamente
            if os.path.exists(caminho_pdf):
                messagebox.showinfo("Sucesso", f"Arquivo PDF com as etiquetas gerado com sucesso! (Arquivo: {caminho_pdf})")
            else:
                messagebox.showerror("Erro", "Erro ao gerar o PDF.")
        
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar o PDF: {e}")


criar_banco()  # Cria o banco de dados e as tabelas
interface()  # Inicia a interface gráfica