"""
Módulo Gerador de Relatório PDF.

Recupera os dados de performance do SQLite, gera gráficos comparativos
com matplotlib, e cria um relatório em PDF descrevendo os resultados.
"""

import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

from logger.db_logger import OperationLogger

# src/report/ → src/ → project root
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output", "reports")
PLOTS_DIR = os.path.join(REPORT_DIR, "plots")


class PerformanceReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        # Arial substituída por Helvetica
        self.cell(0, 10, "Relatório de Performance - Criptografia & Esteganografia", 0, 1, "C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

    def add_chapter_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, "L", 1)
        self.ln(4)

    def add_chapter_body(self, text):
        self.set_font("Helvetica", "", 11)
        self.multi_cell(0, 7, text)
        self.ln()


def generate_plots(df: pd.DataFrame) -> list[str]:
    """Gera gráficos a partir do DataFrame e os salva localmente."""
    os.makedirs(PLOTS_DIR, exist_ok=True)
    plots = []

    if df.empty:
        return plots

    # Converter bytes para MB
    df['size_mb'] = df['file_size_bytes'] / (1024 * 1024)
    # Filtrar apenas operações de benchmark
    df_bench = df[df['operation_type'].str.contains("Benchmark")]

    if df_bench.empty:
        return plots

    # Agrupar por tamanho e algoritmo (Média de tempo)
    enc_df = df_bench[df_bench['operation_type'] == 'Benchmark Encrypt']
    dec_df = df_bench[df_bench['operation_type'] == 'Benchmark Decrypt']
    steg_hide = df_bench[df_bench['operation_type'] == 'Benchmark Ocultar']
    steg_rev = df_bench[df_bench['operation_type'] == 'Benchmark Extrair']

    # --- Plot: Cifragem (Encrypt) ---
    plt.figure(figsize=(10, 6))
    for algo in enc_df['algorithm'].unique():
        data = enc_df[enc_df['algorithm'] == algo].groupby('size_mb')['duration_seconds'].mean()
        plt.plot(data.index, data.values, marker='o', label=algo)

    plt.title("Tempo de Encriptação vs Tamanho do Arquivo")
    plt.xlabel("Tamanho do Arquivo (MB)")
    plt.ylabel("Tempo (Segundos)")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    p1 = os.path.join(PLOTS_DIR, "encrypt_plot.png")
    plt.savefig(p1, bbox_inches='tight')
    plt.close()
    plots.append(p1)

    # --- Plot: Decifragem (Decrypt) ---
    plt.figure(figsize=(10, 6))
    for algo in dec_df['algorithm'].unique():
        data = dec_df[dec_df['algorithm'] == algo].groupby('size_mb')['duration_seconds'].mean()
        plt.plot(data.index, data.values, marker='s', label=algo)

    plt.title("Tempo de Decriptação vs Tamanho do Arquivo")
    plt.xlabel("Tamanho do Arquivo (MB)")
    plt.ylabel("Tempo (Segundos)")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    p2 = os.path.join(PLOTS_DIR, "decrypt_plot.png")
    plt.savefig(p2, bbox_inches='tight')
    plt.close()
    plots.append(p2)

    # --- Plot: Esteganografia ---
    if not steg_hide.empty:
        plt.figure(figsize=(10, 6))
        data_h = steg_hide.groupby('size_mb')['duration_seconds'].mean()
        data_r = steg_rev.groupby('size_mb')['duration_seconds'].mean()
        plt.plot(data_h.index, data_h.values, marker='^', label='Ocultar (Embed)', color='green')
        plt.plot(data_r.index, data_r.values, marker='v', label='Extrair (Extract)', color='red')

        plt.title("Tempo de Esteganografia LSB vs Tamanho do Arquivo Físico")
        plt.xlabel("Tamanho do Arquivo Payload (MB)")
        plt.ylabel("Tempo (Segundos)")
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        p3 = os.path.join(PLOTS_DIR, "stego_plot.png")
        plt.savefig(p3, bbox_inches='tight')
        plt.close()
        plots.append(p3)

    return plots


def create_pdf_report(logger: OperationLogger) -> str:
    """
    Gera o relatório PDF completo baseado no histórico de logs.
    """
    os.makedirs(REPORT_DIR, exist_ok=True)
    pdf_path = os.path.join(REPORT_DIR, "performance_report.pdf")

    # Extrair dados do DB
    logs = logger.get_benchmark_data()
    df = pd.DataFrame(logs)

    pdf = PerformanceReport()
    pdf.add_page()
    
    # Contexto e Funcionamento
    pdf.add_chapter_title("1. Introdução e Funcionamento")
    intro_txt = (
        "Este relatório apresenta a análise de performance das funções criptográficas "
        "e esteganográficas da aplicação. A aplicação utiliza AES-256 (modos CBC e GCM) "
        "para criptografia simétrica e um modelo híbrido RSA-2048 + AES-256 para criptografia "
        "assimétrica de grandes volumes de dados. A esteganografia é baseada na técnica "
        "Least Significant Bit (LSB) aplicada a imagens PNG.\n\n"
        "Todas as operações foram registradas com precisão e os dados coletados abaixo "
        "são correspondentes aos tamanhos de arquivo executados no benchmark (10MB, 50MB, "
        "100MB, 250MB, 500MB)."
    )
    pdf.add_chapter_body(intro_txt)

    if df.empty:
        pdf.add_chapter_body("Não há dados de benchmark suficientes no banco de dados para gerar análise. "
                             "Por favor, execute o benchmark na interface da aplicação primeiro.")
        pdf.output(pdf_path)
        return pdf_path

    # Gráficos
    pdf.add_chapter_title("2. Análise Gráfica de Performance")
    plots = generate_plots(df)
    
    for plot_file in plots:
        pdf.image(plot_file, w=170)
        pdf.ln(5)
    
    # Análise de Dados
    pdf.add_page()
    pdf.add_chapter_title("3. Tabela Comparativa de Tempos (Média em Segundos)")

    # Converter e agrupar para tabela
    df['size_mb'] = df['file_size_bytes'] / (1024 * 1024)
    # Pivot table usando mean e cuidando de valores ausentes (ex: stego não roda 500mb)
    pivot_df = df.pivot_table(
        values='duration_seconds', 
        index='size_mb', 
        columns=['operation_type', 'algorithm'], 
        aggfunc='mean'
    )

    pdf.set_font("Helvetica", "", 8)
    # header básico
    pdf.cell(30, 8, "Tamanho(MB)", border=1, align="C")
    
    # Filtrar apenas as ops de benchmark para colunas
    bench_cols = [c for c in pivot_df.columns if "Benchmark" in c[0]]
    
    # Tenta plotar dinamicamente as colunas encontradas
    col_width = 150 / len(bench_cols) if bench_cols else 30
    
    for col in bench_cols:
        op_short = col[0].replace("Benchmark ", "")[0:3] # Enc, Dec, Ocu, Ext
        alg_short = col[1].replace("AES-256-", "")
        # Header string
        hdr = f"{alg_short}-{op_short}"
        pdf.cell(col_width, 8, hdr, border=1, align="C")
    pdf.ln()

    # Dados
    for size in pivot_df.index:
        pdf.cell(30, 8, f"{size:.1f}", border=1, align="C")
        row_data = pivot_df.loc[size]
        for col in bench_cols:
            val = row_data.get(col)
            if pd.isna(val):
                txt_val = "-"
            else:
                txt_val = f"{val:.3f}s"
            pdf.cell(col_width, 8, txt_val, border=1, align="C")
        pdf.ln()

    # Conclusão
    pdf.ln(10)
    pdf.add_chapter_title("4. Conclusões")
    conc_text = (
        "- AES-GCM geralmente demonstra perfis de segurança e integridade superiores ao AES-CBC, "
        "com impacto de performance quase imperceptível devido à aceleração em hardware modernas.\n"
        "- A criptografia Assimétrica pura de arquivos grandes é inviável, justificando a eficiência da "
        "arquitetura híbrida (RSA cifrando apenas a chave AES).\n"
        "- A esteganografia LSB consome exponencialmente mais tempo e alocação de memória (RAM) à medida "
        "que o arquivo payload aumenta, visto que requer manipulação direta dos canais RGB da imagem; "
        "razão pela qual limitou-se sua execução no benchmark a 50MB."
    )
    pdf.add_chapter_body(conc_text)

    # Historico
    pdf.add_chapter_title("5. Histórico Recente de Operações (Últimas 10)")
    all_logs = logger.get_all_logs()[:10]
    
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(35, 6, "Data/Hora", border=1, align="C")
    pdf.cell(30, 6, "Operação", border=1, align="C")
    pdf.cell(35, 6, "Algoritmo", border=1, align="C")
    pdf.cell(20, 6, "Bytes", border=1, align="C")
    pdf.cell(15, 6, "Tempo(s)", border=1, align="C")
    pdf.cell(50, 6, "Info/Key", border=1, align="C")
    pdf.ln()
    for log in all_logs:
        pdf.cell(35, 6, log['timestamp'][:19], border=1)
        pdf.cell(30, 6, log['operation_type'][:15], border=1)
        pdf.cell(35, 6, log['algorithm'][:15], border=1)
        pdf.cell(20, 6, str(log['file_size_bytes']), border=1, align="R")
        pdf.cell(15, 6, f"{log['duration_seconds']:.2f}", border=1, align="R")
        # Limita o tamanho visual da informação da chave
        ki = log['key_info'][:30] if log['key_info'] else ''
        pdf.cell(50, 6, ki, border=1)
        pdf.ln()

    # Salva
    pdf.output(pdf_path)
    return pdf_path

