"""
Módulo de Benchmark.

Gera arquivos de diversos tamanhos, executa os algoritmos de criptografia
(AES-CBC, AES-GCM, RSA-híbrido) e esteganografia, e mede a performance.
"""

import os
import secrets
from PIL import Image

from logger.db_logger import OperationLogger, timed_operation
from crypto import symmetric, asymmetric
from stego import lsb

BENCHMARK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "benchmark")


def _generate_test_file(size_mb: int, filepath: str):
    """Gera um arquivo preenchido com bytes aleatórios do tamanho especificado."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        if os.path.getsize(filepath) == size_mb * 1024 * 1024:
            return  # Já existe e tem o tamanho correto

    print(f"Gerando arquivo de teste de {size_mb}MB: {filepath}")
    chunk_size = 1024 * 1024  # 1MB
    with open(filepath, "wb") as f:
        for _ in range(size_mb):
            f.write(secrets.token_bytes(chunk_size))


def _generate_test_image(size_mb: int, filepath: str):
    """
    Gera uma imagem de teste capaz de armazenar os dados necessários.
    Como a esteganografia LSB armazena 1 bit por canal, precisamos de 8 bytes
    de dados de imagem para cada byte de payload (em RGB, são 3 canais por pixel).

    Para simplificar no benchmark, geramos uma imagem retangular grande o
    suficiente. Porém imagens de 500MB de RAM podem travar o PC do usuário.
    Limitaremos o benchmark de esteganografia a até 50MB.
    """
    if size_mb > 50:
        return None  # Pular estego para arquivos enormes

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    # Aproximação segura: (size_mb * 3_200_000) pixels
    total_pixels = size_mb * 3_200_000
    width = int(total_pixels ** 0.5)
    height = width

    if os.path.exists(filepath):
        try:
            with Image.open(filepath) as img:
                if img.width >= width and img.height >= height:
                    return filepath
        except Exception:
            pass
        os.remove(filepath)

    print(f"Gerando imagem de teste LSB para {size_mb}MB: {filepath} ({width}x{height})")
    img = Image.new('RGB', (width, height), color='blue')
    img.save(filepath, format="PNG")
    return filepath


def run_benchmarks(sizes_mb: list[int], logger: OperationLogger, progress_callback=None):
    """
    Executa os benchmarks para os tamanhos especificados.

    Args:
        sizes_mb: Lista de tamanhos em MB (ex: [10, 50, 100, 250, 500]).
        logger: Instância de OperationLogger para registrar os tempos.
        progress_callback: Função opcional para atualizar interface gráfica.
    """
    os.makedirs(BENCHMARK_DIR, exist_ok=True)

    # Chave e Senha fixos para o benchmark
    aes_pwd = "benchmark_password"
    aes_key, _ = symmetric.derive_key_from_password(aes_pwd, salt=b"bench_salt_12345")
    priv_key, pub_key = asymmetric.generate_rsa_keypair(2048)

    total_ops = len(sizes_mb) * 6  # 3 algos * 2 (enc/dec) + stego (enc/dec limitados)
    current_op = 0

    def update_progress(msg: str):
        nonlocal current_op
        current_op += 1
        if progress_callback:
            progress_callback(current_op, total_ops, msg)
        else:
            print(f"[{current_op}/{total_ops}] {msg}")

    for size in sizes_mb:
        test_file = os.path.join(BENCHMARK_DIR, f"test_{size}MB.bin")
        _generate_test_file(size, test_file)

        # AES-GCM
        out_enc = os.path.join(BENCHMARK_DIR, f"gcm_enc_{size}MB.bin")
        out_dec = os.path.join(BENCHMARK_DIR, f"gcm_dec_{size}MB.bin")

        @timed_operation(logger, "Benchmark Encrypt", "AES-256-GCM")
        def bm_gcm_enc(): return symmetric.encrypt_aes_gcm(test_file, out_enc, aes_key)
        bm_gcm_enc()
        update_progress(f"AES-GCM Encrypt {size}MB")

        @timed_operation(logger, "Benchmark Decrypt", "AES-256-GCM")
        def bm_gcm_dec(): return symmetric.decrypt_aes_gcm(out_enc, out_dec, aes_key)
        bm_gcm_dec()
        update_progress(f"AES-GCM Decrypt {size}MB")

        # AES-CBC
        out_enc = os.path.join(BENCHMARK_DIR, f"cbc_enc_{size}MB.bin")
        out_dec = os.path.join(BENCHMARK_DIR, f"cbc_dec_{size}MB.bin")

        @timed_operation(logger, "Benchmark Encrypt", "AES-256-CBC")
        def bm_cbc_enc(): return symmetric.encrypt_aes_cbc(test_file, out_enc, aes_key)
        bm_cbc_enc()
        update_progress(f"AES-CBC Encrypt {size}MB")

        @timed_operation(logger, "Benchmark Decrypt", "AES-256-CBC")
        def bm_cbc_dec(): return symmetric.decrypt_aes_cbc(out_enc, out_dec, aes_key)
        bm_cbc_dec()
        update_progress(f"AES-CBC Decrypt {size}MB")

        # RSA-Hibrido
        out_enc = os.path.join(BENCHMARK_DIR, f"rsa_enc_{size}MB.bin")
        out_dec = os.path.join(BENCHMARK_DIR, f"rsa_dec_{size}MB.bin")

        @timed_operation(logger, "Benchmark Encrypt", "RSA-2048 Híbrido")
        def bm_rsa_enc(): return asymmetric.encrypt_rsa(test_file, out_enc, pub_key)
        bm_rsa_enc()
        update_progress(f"RSA-Híbrido Encrypt {size}MB")

        @timed_operation(logger, "Benchmark Decrypt", "RSA-2048 Híbrido")
        def bm_rsa_dec(): return asymmetric.decrypt_rsa(out_enc, out_dec, priv_key)
        bm_rsa_dec()
        update_progress(f"RSA-Híbrido Decrypt {size}MB")

        # Esteganografia (apenas se <= 50MB por restrições de memória/tempo excessivo de RAM no PIL)
        if size <= 50:
            img_file = os.path.join(BENCHMARK_DIR, f"stego_img_{size}MB.png")
            img_out = os.path.join(BENCHMARK_DIR, f"stego_out_{size}MB.png")
            _generate_test_image(size, img_file)

            @timed_operation(logger, "Benchmark Ocultar", "Estego-LSB")
            def bm_steg_enc(): return lsb.hide_file(img_file, test_file, img_out)
            bm_steg_enc()
            update_progress(f"Esteganografia Ocultar {size}MB")

            @timed_operation(logger, "Benchmark Extrair", "Estego-LSB")
            def bm_steg_dec(): return lsb.reveal_file(img_out, BENCHMARK_DIR)
            bm_steg_dec()
            update_progress(f"Esteganografia Extrair {size}MB")
        else:
            # Pula passos
            update_progress(f"Esteganografia Pulo (>50MB)")
            update_progress(f"Esteganografia Pulo (>50MB)")

    print("Benchmark concluído!")
