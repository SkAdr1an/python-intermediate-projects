# finance-manager/finance_manager.py
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# --------- Banco de dados (sempre no diretório do arquivo) ---------
DB_PATH = Path(__file__).resolve().parent / "financas.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        categoria TEXT NOT NULL,
        tipo TEXT CHECK(tipo IN ('entrada','saida')) NOT NULL,
        data TEXT NOT NULL
    )
    """
)
conn.commit()

# --------- Funções de dados ---------
def adicionar_transacao(descricao: str, valor: float, categoria: str, tipo: str) -> None:
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute(
            "INSERT INTO transacoes (descricao, valor, categoria, tipo, data) VALUES (?, ?, ?, ?, ?)",
            (descricao, valor, categoria, tipo, data_atual),
        )
        conn.commit()
    except sqlite3.Error as e:
        messagebox.showerror("Erro", f"Falha ao inserir no banco: {e}")
        return
    messagebox.showinfo("Sucesso", "Transação adicionada com sucesso!")

def obter_saldo() -> float:
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo = 'entrada'")
    entradas = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo = 'saida'")
    saidas = cursor.fetchone()[0] or 0.0
    return entradas - saidas

def obter_transacoes():
    cursor.execute("SELECT * FROM transacoes ORDER BY datetime(data) DESC, id DESC")
    return cursor.fetchall()

def remover_transacao(id_transacao: int) -> None:
    try:
        cursor.execute("DELETE FROM transacoes WHERE id = ?", (id_transacao,))
        conn.commit()
    except sqlite3.Error as e:
        messagebox.showerror("Erro", f"Falha ao remover: {e}")
        return
    messagebox.showinfo("Sucesso", "Transação removida com sucesso!")

def exportar_csv(path: Path) -> None:
    try:
        cursor.execute("SELECT * FROM transacoes ORDER BY id")
        rows = cursor.fetchall()
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "descricao", "valor", "categoria", "tipo", "data"])
            w.writerows(rows)
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao exportar CSV: {e}")
        return
    messagebox.showinfo("Sucesso", f"Exportado para {path.name}")

# --------- Gráfico ---------
def gerar_grafico(salvar: bool = False) -> None:
    cursor.execute("SELECT tipo, SUM(valor) FROM transacoes GROUP BY tipo")
    resultados = cursor.fetchall()
    if not resultados:
        messagebox.showerror("Erro", "Nenhuma transação para gerar gráfico.")
        return

    labels = [row[0].capitalize() for row in resultados]
    valores = [row[1] for row in resultados]

    try:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(valores, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title("Distribuição de Entradas e Saídas")

        # Detalhes
        cursor.execute("SELECT descricao, valor, tipo FROM transacoes ORDER BY id DESC LIMIT 12")
        detalhes = cursor.fetchall()
        entradas = [f"{d}: R$ {v:.2f}" for d, v, t in detalhes if t == "entrada"]
        saidas = [f"{d}: R$ {v:.2f}" for d, v, t in detalhes if t == "saida"]

        info_text = (
            "Entradas recentes:\n" + ("\n".join(entradas) if entradas else "Nenhuma")
            + "\n\nSaídas recentes:\n" + ("\n".join(saidas) if saidas else "Nenhuma")
        )
        fig.subplots_adjust(bottom=0.2)
        fig.text(0.5, 0.02, info_text, ha="center", fontsize=9, wrap=True)

        if salvar:
            file_name = f"grafico_financas_{datetime.now():%Y%m%d_%H%M%S}.png"
            fig.savefig(file_name, dpi=150)
            messagebox.showinfo("Sucesso", f"Gráfico salvo como {file_name}")
        else:
            plt.show()
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao gerar gráfico: {e}")

# --------- UI (Tkinter) ---------
def interface_usuario():
    def adicionar():
        descricao = entry_descricao.get().strip()
        valor_txt = entry_valor.get().strip()
        categoria = entry_categoria.get().strip()
        tipo = combo_tipo.get().strip()

        if not (descricao and valor_txt and categoria and tipo):
            messagebox.showerror("Erro", "Preencha todos os campos.")
            return

        try:
            valor = float(valor_txt.replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "O valor deve ser numérico.")
            return

        if valor <= 0:
            messagebox.showerror("Erro", "O valor deve ser positivo.")
            return

        adicionar_transacao(descricao, valor, categoria, tipo)
        atualizar_interface()
        entry_descricao.delete(0, tk.END)
        entry_valor.delete(0, tk.END)
        entry_categoria.delete(0, tk.END)
        combo_tipo.current(0)

    def remover():
        sel = tree.selection()
        if not sel:
            messagebox.showerror("Erro", "Selecione uma transação para remover.")
            return

        # pega apenas o primeiro item selecionado
        item_id = sel[0]
        values = tree.item(item_id, "values")
        id_transacao = int(values[0])

        # confirmação simples (evita senha fixa no código)
        if messagebox.askyesno("Confirmação", f"Remover a transação ID {id_transacao}?"):
            remover_transacao(id_transacao)
            atualizar_interface()

    def atualizar_interface():
        # saldo
        saldo = obter_saldo()
        label_saldo.config(text=f"Saldo Total: R$ {saldo:.2f}")

        # tabela
        for row in tree.get_children():
            tree.delete(row)
        for transacao in obter_transacoes():
            tree.insert("", "end", values=transacao)

    def exibir_grafico():
        gerar_grafico(False)

    def salvar_grafico():
        gerar_grafico(True)

    def exportar():
        nome = f"transacoes_{datetime.now():%Y%m%d_%H%M%S}.csv"
        exportar_csv(Path(__file__).resolve().parent / nome)

    root = tk.Tk()
    root.title("Gerenciador de Finanças do Adrian")

    frame_topo = tk.Frame(root, pady=10)
    frame_topo.pack()

    tk.Label(frame_topo, text="Descrição:").grid(row=0, column=0, padx=5, sticky="w")
    entry_descricao = tk.Entry(frame_topo, width=30)
    entry_descricao.grid(row=0, column=1, padx=5)

    tk.Label(frame_topo, text="Valor (R$):").grid(row=1, column=0, padx=5, sticky="w")
    entry_valor = tk.Entry(frame_topo, width=30)
    entry_valor.grid(row=1, column=1, padx=5)

    tk.Label(frame_topo, text="Categoria:").grid(row=2, column=0, padx=5, sticky="w")
    entry_categoria = tk.Entry(frame_topo, width=30)
    entry_categoria.grid(row=2, column=1, padx=5)

    tk.Label(frame_topo, text="Tipo:").grid(row=3, column=0, padx=5, sticky="w")
    combo_tipo = ttk.Combobox(frame_topo, values=["entrada", "saida"], state="readonly", width=27)
    combo_tipo.grid(row=3, column=1, padx=5)
    combo_tipo.current(0)  # valor padrão

    tk.Button(frame_topo, text="Adicionar Transação", command=adicionar).grid(row=4, column=1, pady=10, sticky="e")

    label_saldo = tk.Label(root, text="Saldo Total: R$ 0.00", font=("Arial", 16))
    label_saldo.pack(pady=10)

    frame_tabela = tk.Frame(root)
    frame_tabela.pack(fill="both", expand=True)

    colunas = ("ID", "Descrição", "Valor", "Categoria", "Tipo", "Data")
    tree = ttk.Treeview(frame_tabela, columns=colunas, show="headings", selectmode="browse")
    for c in colunas:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    frame_botoes = tk.Frame(root, pady=10)
    frame_botoes.pack()
    tk.Button(frame_botoes, text="Gerar Gráfico", command=exibir_grafico).grid(row=0, column=0, padx=8)
    tk.Button(frame_botoes, text="Salvar Gráfico", command=salvar_grafico).grid(row=0, column=1, padx=8)
    tk.Button(frame_botoes, text="Exportar CSV", command=exportar).grid(row=0, column=2, padx=8)
    tk.Button(frame_botoes, text="Remover Transação", command=remover).grid(row=0, column=3, padx=8)

    atualizar_interface()
    root.mainloop()

def main():
    try:
        interface_usuario()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
