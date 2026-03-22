"""
Interface Gráfica usando customtkinter.
"""

import os
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk

from PIL import Image
from logger.db_logger import OperationLogger, timed_operation
from crypto import symmetric, asymmetric
from stego import lsb
from benchmark import runner
from report import pdf_report

# Configuração global de aparência
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class CryptoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cripto & Estego Pro")
        self.geometry("900x650")
        self.minsize(800, 600)

        # Inicializa Logger
        self.logger = OperationLogger()

        # Layout Main
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_sym = self.tabview.add("Simétrica")
        self.tab_asym = self.tabview.add("Assimétrica")
        self.tab_stego = self.tabview.add("Esteganografia")
        self.tab_logs = self.tabview.add("Logs")
        self.tab_bench = self.tabview.add("Benchmark")
        self.tab_graphs = self.tabview.add("Gráficos")

        self._build_symmetric_tab()
        self._build_asymmetric_tab()
        self._build_stego_tab()
        self._build_logs_tab()
        self._build_benchmark_tab()
        self._build_graphs_tab()

    # --- Utils ---
    def _select_file(self, string_var: ctk.StringVar, title="Selecione um arquivo"):
        filename = filedialog.askopenfilename(title=title)
        if filename:
            string_var.set(filename)

    def _select_save_file(self, string_var: ctk.StringVar, title="Salvar como"):
        filename = filedialog.asksaveasfilename(title=title)
        if filename:
            string_var.set(filename)

    def _show_loading(self, is_loading: bool, progress_bar: ctk.CTkProgressBar, button: ctk.CTkButton):
        if is_loading:
            progress_bar.set(0)
            progress_bar.grid()
            progress_bar.start()
            button.configure(state="disabled")
        else:
            progress_bar.stop()
            progress_bar.grid_remove()
            button.configure(state="normal")
            self._refresh_logs()

    def _run_in_thread(self, func, progress_bar, button, *args, **kwargs):
        def wrapper():
            self._show_loading(True, progress_bar, button)
            try:
                func(*args, **kwargs)
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Erro", f"Ocorreu um erro: {err_msg}"))
            finally:
                self._show_loading(False, progress_bar, button)

        threading.Thread(target=wrapper, daemon=True).start()

    # --- Aba: Simétrica ---
    def _build_symmetric_tab(self):
        self.tab_sym.grid_columnconfigure((0, 1), weight=1)

        # Variáveis
        input_var = ctk.StringVar()
        output_var = ctk.StringVar()
        password_var = ctk.StringVar()
        mode_var = ctk.StringVar(value="AES-256-GCM")

        # UI
        ctk.CTkLabel(self.tab_sym, text="Arquivo de Entrada:", anchor="w").grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_sym, textvariable=input_var, width=400).grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_sym, text="Procurar", command=lambda: self._select_file(input_var)).grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.tab_sym, text="Arquivo de Saída:", anchor="w").grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_sym, textvariable=output_var, width=400).grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_sym, text="Salvar Como", command=lambda: self._select_save_file(output_var)).grid(row=3, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.tab_sym, text="Senha do Arquivo:", anchor="w").grid(row=4, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_sym, textvariable=password_var, show="*", width=400).grid(row=5, column=0, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.tab_sym, text="Modo de Operação:", anchor="w").grid(row=6, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkOptionMenu(self.tab_sym, variable=mode_var, values=["AES-256-GCM", "AES-256-CBC"]).grid(row=7, column=0, padx=10, pady=5, sticky="w")

        # Botões
        btn_frame = ctk.CTkFrame(self.tab_sym, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, pady=20)

        progress = ctk.CTkProgressBar(self.tab_sym, mode="indeterminate")
        progress.grid(row=9, column=0, columnspan=2, pady=10, sticky="ew")
        progress.grid_remove()

        btn_enc = ctk.CTkButton(btn_frame, text="Criptografar", command=lambda: self._sym_action("encrypt", input_var.get(), output_var.get(), password_var.get(), mode_var.get(), progress, btn_enc, btn_dec))
        btn_enc.grid(row=0, column=0, padx=10)

        btn_dec = ctk.CTkButton(btn_frame, text="Decriptografar", command=lambda: self._sym_action("decrypt", input_var.get(), output_var.get(), password_var.get(), mode_var.get(), progress, btn_enc, btn_dec))
        btn_dec.grid(row=0, column=1, padx=10)

    def _sym_action(self, action, input_path, output_path, password, mode, progress, btn1, btn2):
        if not input_path or not output_path or not password:
            messagebox.showwarning("Aviso", "Preencha todos os campos (Entrada, Saída e Senha).")
            return

        def task():
            # Derivar chave. Simplificado para o exemplo (salt estático ou gerado para salvar no arquivo não implementado na UI, apenas usando key gen simples ou salt vazio)
            # Para segurança real, o salt deveria ser gerado no enc e salvo junto.
            # Como a db pede metadados, vamos gerar uma chave de teste ou gerenciar o salt simplificado.
            # Aqui vamos usar uma chave estática baseada na senha (não recomendado p/ prod, mas atende o mockup)
            key, _ = symmetric.derive_key_from_password(password, salt=b"fixed_salt_1234")

            if mode == "AES-256-GCM":
                func = symmetric.encrypt_aes_gcm if action == "encrypt" else symmetric.decrypt_aes_gcm
            else:
                func = symmetric.encrypt_aes_cbc if action == "encrypt" else symmetric.decrypt_aes_cbc

            alg_name = f"{mode}"
            op_name = "Cifrar (Simétrica)" if action == "encrypt" else "Decifrar (Simétrica)"

            @timed_operation(self.logger, op_name, alg_name)
            def run_op():
                return func(input_path, output_path, key)

            result = run_op()
            messagebox.showinfo("Sucesso", result["details"])

        # Desabilita botões temporariamente
        self._run_in_thread(task, progress, btn1)

    # --- Aba: Assimétrica ---
    def _build_asymmetric_tab(self):
        self.tab_asym.grid_columnconfigure((0, 1), weight=1)

        input_var = ctk.StringVar()
        output_var = ctk.StringVar()
        key_var = ctk.StringVar()

        ctk.CTkLabel(self.tab_asym, text="Arquivo de Entrada:", anchor="w").grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_asym, textvariable=input_var, width=400).grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_asym, text="Procurar", command=lambda: self._select_file(input_var)).grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.tab_asym, text="Arquivo de Saída:", anchor="w").grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_asym, textvariable=output_var, width=400).grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_asym, text="Salvar Como", command=lambda: self._select_save_file(output_var)).grid(row=3, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.tab_asym, text="Chave PEM (Púbica para Cifrar, Privada para Decifrar):", anchor="w").grid(row=4, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_asym, textvariable=key_var, width=400).grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_asym, text="Procurar Chave", command=lambda: self._select_file(key_var, title="Selecione Arquivo .pem")).grid(row=5, column=1, padx=10, pady=5)

        btn_frame = ctk.CTkFrame(self.tab_asym, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)

        progress = ctk.CTkProgressBar(self.tab_asym, mode="indeterminate")
        progress.grid(row=7, column=0, columnspan=2, pady=10, sticky="ew")
        progress.grid_remove()

        btn_gen = ctk.CTkButton(btn_frame, text="Gerar Par de Chaves", command=self._gen_rsa_keys)
        btn_gen.grid(row=0, column=0, padx=10)

        btn_enc = ctk.CTkButton(btn_frame, text="Cifrar com Chave Pública", command=lambda: self._asym_action("encrypt", input_var.get(), output_var.get(), key_var.get(), progress, btn_enc))
        btn_enc.grid(row=0, column=1, padx=10)

        btn_dec = ctk.CTkButton(btn_frame, text="Decifrar com Chave Privada", command=lambda: self._asym_action("decrypt", input_var.get(), output_var.get(), key_var.get(), progress, btn_dec))
        btn_dec.grid(row=0, column=2, padx=10)

    def _gen_rsa_keys(self):
        dir_path = filedialog.askdirectory(title="Selecione onde salvar as chaves")
        if not dir_path:
            return

        priv_path = os.path.join(dir_path, "private.pem")
        pub_path = os.path.join(dir_path, "public.pem")

        self.logger.log_operation("Geração de Chaves", "RSA-2048", details="Iniciando geração")
        try:
            priv, pub = asymmetric.generate_rsa_keypair()
            asymmetric.save_private_key(priv, priv_path)
            asymmetric.save_public_key(pub, pub_path)
            messagebox.showinfo("Sucesso", f"Chaves geradas com sucesso em:\n{dir_path}")
            self.logger.log_operation("Geração de Chaves", "RSA-2048", output_file=dir_path, details="Sucesso")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar chaves: {str(e)}")
            self.logger.log_operation("Geração de Chaves", "RSA-2048", details=str(e), status="error")
        self._refresh_logs()

    def _asym_action(self, action, input_path, output_path, key_path, progress, btn):
        if not input_path or not output_path or not key_path:
            messagebox.showwarning("Aviso", "Preencha entrada, saída e selecione a chave.")
            return

        def task():
            if action == "encrypt":
                pub_key = asymmetric.load_public_key(key_path)

                @timed_operation(self.logger, "Cifrar (Assimétrica)", "RSA-2048 Híbrido")
                def run_enc():
                    return asymmetric.encrypt_rsa(input_path, output_path, pub_key)

                res = run_enc()
            else:
                priv_key = asymmetric.load_private_key(key_path)

                @timed_operation(self.logger, "Decifrar (Assimétrica)", "RSA-2048 Híbrido")
                def run_dec():
                    return asymmetric.decrypt_rsa(input_path, output_path, priv_key)

                res = run_dec()

            messagebox.showinfo("Sucesso", res["details"])

        self._run_in_thread(task, progress, btn)

    # --- Aba: Esteganografia ---
    def _build_stego_tab(self):
        self.tab_stego.grid_columnconfigure((0, 1), weight=1)

        img_in_var = ctk.StringVar()
        out_var = ctk.StringVar()

        ctk.CTkLabel(self.tab_stego, text="Imagem Base (PNG):", anchor="w").grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_stego, textvariable=img_in_var, width=400).grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_stego, text="Procurar Imagem", command=lambda: self._select_file(img_in_var, "Selecione PNG")).grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.tab_stego, text="Imagem de Saída (PNG) (se ocultando):", anchor="w").grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")
        ctk.CTkEntry(self.tab_stego, textvariable=out_var, width=400).grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_stego, text="Salvar Como", command=lambda: self._select_save_file(out_var, "Salvar PNG")).grid(row=3, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.tab_stego, text="Mensagem de Texto (em extrações, sairá aqui):", anchor="w").grid(row=4, column=0, padx=10, pady=(10, 0), sticky="w")
        self.stego_textbox = ctk.CTkTextbox(self.tab_stego, height=100)
        self.stego_textbox.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        btn_frame = ctk.CTkFrame(self.tab_stego, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)

        progress = ctk.CTkProgressBar(self.tab_stego, mode="indeterminate")
        progress.grid(row=7, column=0, columnspan=2, pady=10, sticky="ew")
        progress.grid_remove()

        btn_hide = ctk.CTkButton(btn_frame, text="Ocultar Texto", command=lambda: self._stego_hide(img_in_var.get(), out_var.get(), progress, btn_hide))
        btn_hide.grid(row=0, column=0, padx=10)

        btn_reveal = ctk.CTkButton(btn_frame, text="Revelar Texto", command=lambda: self._stego_reveal(img_in_var.get(), progress, btn_reveal))
        btn_reveal.grid(row=0, column=1, padx=10)

    def _stego_hide(self, img_path, out_path, progress, btn):
        text = self.stego_textbox.get("1.0", "end-1c")
        if not img_path or not out_path or not text:
            messagebox.showwarning("Aviso", "Preencha a Imagem Base, Saída e o Texto a ocultar.")
            return

        def task():
            @timed_operation(self.logger, "Ocultar", "Esteganografia LSB (Texto)")
            def run_hide():
                return lsb.hide_message(img_path, text, out_path)

            res = run_hide()
            messagebox.showinfo("Sucesso", res["details"])

        self._run_in_thread(task, progress, btn)

    def _stego_reveal(self, img_path, progress, btn):
        if not img_path:
            messagebox.showwarning("Aviso", "Preencha a Imagem Base esteganografada.")
            return

        def task():
            @timed_operation(self.logger, "Revelar", "Esteganografia LSB (Texto)")
            def run_reveal():
                return lsb.reveal_message(img_path)

            res = run_reveal()
            # UI updates must run on main thread technically, but ctk handles it mostly okay. Safe way:
            self.after(0, lambda: self._update_stego_textbox(res["message"]))
            messagebox.showinfo("Sucesso", res["details"])

        self._run_in_thread(task, progress, btn)

    def _update_stego_textbox(self, text):
        self.stego_textbox.delete("1.0", "end")
        self.stego_textbox.insert("1.0", text)

    # --- Aba: Logs ---
    def _build_logs_tab(self):
        self.tab_logs.grid_rowconfigure(1, weight=1)
        self.tab_logs.grid_columnconfigure(0, weight=1)

        # Barra superior com botões
        top_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(top_frame, text="Atualizar", command=self._refresh_logs).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Limpar Logs", fg_color="#bf1b1b", hover_color="#8f1414", command=self._clear_logs).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Exportar CSV", command=self._export_csv).pack(side="right", padx=5)

        # Scrolled Text para logs
        self.logs_textbox = ctk.CTkTextbox(self.tab_logs)
        self.logs_textbox.grid(row=1, column=0, sticky="nsew")
        self._refresh_logs()

    def _refresh_logs(self):
        if not hasattr(self, 'logs_textbox'):
            return
        self.logs_textbox.configure(state="normal")
        self.logs_textbox.delete("1.0", "end")

        logs = self.logger.get_all_logs()
        if not logs:
            self.logs_textbox.insert("end", "Nenhum log encontrado.\n")
        else:
            for log in logs:
                line = (f"[{log['timestamp']}] {log['operation_type']} "
                        f"({log['algorithm']}) - Status: {log['status']} - "
                        f"Tempo: {log['duration_seconds']}s\n"
                        f"     Infos: {log['details']}\n\n")
                self.logs_textbox.insert("end", line)

        self.logs_textbox.configure(state="disabled")

    def _clear_logs(self):
        if messagebox.askyesno("Confirmar", "Deseja realmente limpar todos os logs?"):
            self.logger.clear_logs()
            self._refresh_logs()

    def _export_csv(self):
        filepath = filedialog.asksaveasfilename(title="Exportar CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if filepath:
            try:
                self.logger.export_csv(filepath)
                messagebox.showinfo("Exportado", f"Logs exportados para {filepath}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro as exportar: {str(e)}")

    # --- Aba: Benchmark e Relatório ---
    def _build_benchmark_tab(self):
        self.tab_bench.grid_columnconfigure(0, weight=1)
        self.tab_bench.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self.tab_bench,
            text=("Executa testes completos criando arquivos temporários de vários tamanhos.\n"
                  "Atenção: Isso pode levar vários minutos e consumir espaço em disco."),
            justify="center"
        ).grid(row=0, column=0, pady=(15, 5))

        # Frame checkboxes
        check_frame = ctk.CTkFrame(self.tab_bench, fg_color="transparent")
        check_frame.grid(row=1, column=0, pady=5)

        self.bench_vars = {
            10: ctk.BooleanVar(value=True),
            25: ctk.BooleanVar(value=True),
            50: ctk.BooleanVar(value=True),
            100: ctk.BooleanVar(value=True),
            250: ctk.BooleanVar(value=True),
            500: ctk.BooleanVar(value=False), # 500 desativado por padrão (demorado)
        }

        ctk.CTkLabel(check_frame, text="Tamanhos a testar:").grid(row=0, column=0, columnspan=5, pady=(0, 10))
        for i, (size, var) in enumerate(self.bench_vars.items()):
            ctk.CTkCheckBox(check_frame, text=f"{size} MB", variable=var).grid(row=1, column=i, padx=10)

        # Botões
        btn_frame = ctk.CTkFrame(self.tab_bench, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=10)

        self.btn_run_bench = ctk.CTkButton(btn_frame, text="Executar Benchmark", command=self._run_benchmark_action)
        self.btn_run_bench.grid(row=0, column=0, padx=10)

        self.btn_gen_pdf = ctk.CTkButton(btn_frame, text="Gerar Relatório PDF", command=self._generate_pdf_action)
        self.btn_gen_pdf.grid(row=0, column=1, padx=10)

        # Scrollable frame para progresso individual por operação
        self.bench_scroll = ctk.CTkScrollableFrame(self.tab_bench, label_text="Progresso das Operações")
        self.bench_scroll.grid(row=3, column=0, sticky="nsew", padx=20, pady=(5, 5))
        self.bench_scroll.grid_columnconfigure(1, weight=1)
        self.bench_scroll.grid_remove()

        # Label de progresso geral
        self.bench_lbl_progress = ctk.CTkLabel(self.tab_bench, text="")
        self.bench_lbl_progress.grid(row=4, column=0, pady=(0, 10))

        self.bench_op_widgets = {}

    def _run_benchmark_action(self):
        selected_sizes = [size for size, var in self.bench_vars.items() if var.get()]
        if not selected_sizes:
            messagebox.showwarning("Aviso", "Selecione pelo menos um tamanho para teste.")
            return
            
        if not messagebox.askyesno("Confirmar", "Iniciar benchmark? Isso pode demorar."):
            return

        self.btn_run_bench.configure(state="disabled")
        self.btn_gen_pdf.configure(state="disabled")

        # Limpar linhas anteriores
        for widget in self.bench_scroll.winfo_children():
            widget.destroy()
        self.bench_op_widgets = {}
        self.bench_scroll.grid()
        self.bench_lbl_progress.configure(text="Iniciando...")

        def update_ui(current, total, msg, status="done"):
            def cb():
                if status == "running":
                    # Criar nova linha para esta operação
                    row = ctk.CTkFrame(self.bench_scroll, fg_color="transparent")
                    row.pack(fill="x", pady=2, padx=5)
                    row.columnconfigure(1, weight=1)

                    status_lbl = ctk.CTkLabel(row, text="⏳", width=30)
                    status_lbl.grid(row=0, column=0, padx=(0, 5))

                    name_lbl = ctk.CTkLabel(row, text=msg, anchor="w")
                    name_lbl.grid(row=0, column=1, sticky="ew")

                    prog = ctk.CTkProgressBar(row, mode="indeterminate", width=120, height=10)
                    prog.grid(row=0, column=2, padx=(10, 0))
                    prog.start()

                    self.bench_op_widgets[msg] = (status_lbl, prog, row)
                    self.bench_lbl_progress.configure(text=f"[{current}/{total}] Executando: {msg}")

                elif status == "done":
                    if msg in self.bench_op_widgets:
                        # Operação concluída — parar barra e marcar como feita
                        status_lbl, prog, row = self.bench_op_widgets[msg]
                        prog.stop()
                        prog.configure(mode="determinate")
                        prog.set(1.0)
                        status_lbl.configure(text="✅")
                    else:
                        # Operação pulada (stego >100MB) — criar linha já concluída
                        row = ctk.CTkFrame(self.bench_scroll, fg_color="transparent")
                        row.pack(fill="x", pady=2, padx=5)
                        row.columnconfigure(1, weight=1)

                        ctk.CTkLabel(row, text="⏭️", width=30).grid(row=0, column=0, padx=(0, 5))
                        ctk.CTkLabel(row, text=msg, anchor="w").grid(row=0, column=1, sticky="ew")

                        prog = ctk.CTkProgressBar(row, mode="determinate", width=120, height=10)
                        prog.grid(row=0, column=2, padx=(10, 0))
                        prog.set(1.0)

                    self.bench_lbl_progress.configure(text=f"[{current}/{total}] concluído")

            self.after(0, cb)

        def task():
            try:
                runner.run_benchmarks(selected_sizes, self.logger, update_ui)
                self.after(0, lambda: messagebox.showinfo("Sucesso", "Benchmark finalizado com sucesso!"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Erro", f"Ocorreu um erro no benchmark: {err_msg}"))
            finally:
                def finalize():
                    self.bench_lbl_progress.configure(text="Benchmark concluído!")
                    self.btn_run_bench.configure(state="normal")
                    self.btn_gen_pdf.configure(state="normal")
                    self._refresh_logs()
                self.after(0, finalize)

        threading.Thread(target=task, daemon=True).start()

    def _generate_pdf_action(self):
        self.btn_gen_pdf.configure(state="disabled")
        def task():
            try:
                pdf_path = pdf_report.create_pdf_report(self.logger)
                self.after(0, lambda: messagebox.showinfo("Relatório Gerado", f"Relatório PDF salvo com sucesso em:\n{pdf_path}"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao gerar o PDF: {err_msg}"))
            finally:
                self.after(0, lambda: self.btn_gen_pdf.configure(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    # --- Aba: Gráficos de Performance ---
    def _build_graphs_tab(self):
        self.tab_graphs.grid_rowconfigure(2, weight=1)
        self.tab_graphs.grid_columnconfigure(0, weight=1)

        # Controles superiores
        ctrl_frame = ctk.CTkFrame(self.tab_graphs, fg_color="transparent")
        ctrl_frame.grid(row=0, column=0, pady=10, sticky="ew")

        ctk.CTkLabel(ctrl_frame, text="Selecione o Gráfico:").pack(side="left", padx=10)

        self.graph_opt_var = ctk.StringVar(value="Cifragem (Encrypt)")
        self.graph_menu = ctk.CTkOptionMenu(
            ctrl_frame, 
            variable=self.graph_opt_var, 
            values=["Cifragem (Encrypt)", "Decifragem (Decrypt)", "Esteganografia"],
            command=self._load_selected_graph
        )
        self.graph_menu.pack(side="left", padx=10)

        self.btn_refresh_graphs = ctk.CTkButton(ctrl_frame, text="Atualizar Gráficos (Gerar Novamente)", command=self._refresh_graphs_action)
        self.btn_refresh_graphs.pack(side="left", padx=20)

        # Label de status
        self.graph_status = ctk.CTkLabel(self.tab_graphs, text="Nenhum dado carregado.")
        self.graph_status.grid(row=1, column=0, pady=5)

        # Area para a imagem
        self.graph_img_lbl = ctk.CTkLabel(self.tab_graphs, text="")
        self.graph_img_lbl.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

    def _refresh_graphs_action(self):
        self.graph_status.configure(text="Gerando gráficos...")
        self.btn_refresh_graphs.configure(state="disabled")

        def task():
            try:
                # Buscar do banco de dados e gerar imagens em disco na pasta de reports
                import pandas as pd
                logs = self.logger.get_benchmark_data()
                df = pd.DataFrame(logs)
                if df.empty or not df['operation_type'].str.contains("Benchmark").any():
                    self.after(0, lambda: self.graph_status.configure(text="Nenhum dado de benchmark no banco de dados. Execute a aba Benchmark primeiro."))
                    return
                # Chama a função do pdf_report para sobrescrever os gráficos na pasta PLOTS_DIR
                pdf_report.generate_plots(df)
                
                self.after(0, lambda: self.graph_status.configure(text="Gráficos atualizados com sucesso."))
                self.after(0, self._load_selected_graph)
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self.graph_status.configure(text=f"Erro: {err_msg}"))
            finally:
                self.after(0, lambda: self.btn_refresh_graphs.configure(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def _load_selected_graph(self, choice=None):
        if not choice:
            choice = self.graph_opt_var.get()
            
        file_map = {
            "Cifragem (Encrypt)": "encrypt_plot.png",
            "Decifragem (Decrypt)": "decrypt_plot.png",
            "Esteganografia": "stego_plot.png"
        }
        
        filename = file_map.get(choice)
        if not filename:
            return
            
        filepath = os.path.join(pdf_report.PLOTS_DIR, filename)
        
        if not os.path.exists(filepath):
            self.graph_status.configure(text="Gráfico não encontrado. Tente 'Atualizar Gráficos'.")
            self.graph_img_lbl.configure(image="")
            return

        try:
            # Carregar a imagem com PIL e CTkImage
            img = Image.open(filepath)
            
            # Ajustar para caber na tela mantendo proporção (ex: largura max 800)
            base_width = 800
            if img.width > base_width:
                wpercent = (base_width / float(img.width))
                hsize = int((float(img.height) * float(wpercent)))
            else:
                base_width = img.width
                hsize = img.height
                
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(base_width, hsize))
            
            self.graph_img_lbl.configure(image=ctk_img)
            self.graph_status.configure(text=f"Exibindo: {choice}")
            
        except Exception as e:
            self.graph_status.configure(text=f"Erro ao carregar imagem: {str(e)}")


def start_app():
    app = CryptoApp()
    app.mainloop()

if __name__ == "__main__":
    start_app()
