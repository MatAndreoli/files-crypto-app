"""
Módulo de logging de operações em banco SQLite.

Registra todas as operações de criptografia e esteganografia
com timestamps, tempos de execução e metadados.
"""

import sqlite3
import os
import time
import csv
import functools
from datetime import datetime
from contextlib import contextmanager


import sys

if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    # For a one-file executable, sys.executable points to the exe
    # sys._MEIPASS points to the temp directory where the bundle is unpacked
    base_dir = os.path.dirname(sys.executable)
    DB_DIR = os.path.join(base_dir, "logs")
else:
    # src/logger/ → src/ → project root
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")

DB_PATH = os.path.join(DB_DIR, "operations.db")


class OperationLogger:
    """Gerenciador de logs de operações em SQLite."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Cria a tabela de operações se não existir."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    input_file TEXT,
                    output_file TEXT,
                    key_info TEXT,
                    file_size_bytes INTEGER,
                    duration_seconds REAL,
                    status TEXT NOT NULL DEFAULT 'success',
                    details TEXT
                )
            """)

    @contextmanager
    def _connect(self):
        """Context manager para conexão com o banco."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def log_operation(
        self,
        operation_type: str,
        algorithm: str,
        input_file: str = "",
        output_file: str = "",
        key_info: str = "",
        file_size_bytes: int = 0,
        duration_seconds: float = 0.0,
        status: str = "success",
        details: str = "",
    ) -> int:
        """
        Registra uma operação no banco de dados.

        Returns:
            ID do registro inserido.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO operations
                    (timestamp, operation_type, algorithm, input_file, output_file,
                     key_info, file_size_bytes, duration_seconds, status, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    operation_type,
                    algorithm,
                    input_file,
                    output_file,
                    key_info,
                    file_size_bytes,
                    duration_seconds,
                    status,
                    details,
                ),
            )
            return cursor.lastrowid

    def get_all_logs(self) -> list[dict]:
        """Retorna todos os logs como lista de dicionários."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM operations ORDER BY id DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_logs_by_type(self, operation_type: str) -> list[dict]:
        """Retorna logs filtrados por tipo de operação."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM operations WHERE operation_type = ? ORDER BY id DESC",
                (operation_type,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_logs_by_algorithm(self, algorithm: str) -> list[dict]:
        """Retorna logs filtrados por algoritmo."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM operations WHERE algorithm = ? ORDER BY id DESC",
                (algorithm,),
            ).fetchall()
            return [dict(row) for row in rows]

    def clear_logs(self):
        """Remove todos os logs."""
        with self._connect() as conn:
            conn.execute("DELETE FROM operations")

    def export_csv(self, output_path: str) -> str:
        """
        Exporta todos os logs para um arquivo CSV.

        Returns:
            Caminho do arquivo CSV gerado.
        """
        logs = self.get_all_logs()
        if not logs:
            return ""

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=logs[0].keys())
            writer.writeheader()
            writer.writerows(logs)
        return output_path

    def get_benchmark_data(self) -> list[dict]:
        """Retorna dados formatados para análise de benchmark."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT algorithm, operation_type, file_size_bytes, duration_seconds
                FROM operations
                WHERE status = 'success'
                    AND file_size_bytes > 0
                    AND duration_seconds > 0
                ORDER BY algorithm, file_size_bytes
                """
            ).fetchall()
            return [dict(row) for row in rows]


def timed_operation(logger: OperationLogger, operation_type: str, algorithm: str):
    """
    Decorador que mede o tempo de execução e registra no logger.

    O decorador espera que a função decorada retorne um dicionário com:
        - input_file: caminho do arquivo de entrada
        - output_file: caminho do arquivo de saída
        - file_size_bytes: tamanho do arquivo em bytes
        - key_info: informações sobre a chave usada (opcional)
        - details: detalhes adicionais (opcional)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            status = "success"
            result = {}
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                result = {"details": str(e)}
                raise
            finally:
                duration = time.perf_counter() - start
                logger.log_operation(
                    operation_type=operation_type,
                    algorithm=algorithm,
                    input_file=result.get("input_file", ""),
                    output_file=result.get("output_file", ""),
                    key_info=result.get("key_info", ""),
                    file_size_bytes=result.get("file_size_bytes", 0),
                    duration_seconds=round(duration, 6),
                    status=status,
                    details=result.get("details", ""),
                )

        return wrapper

    return decorator
