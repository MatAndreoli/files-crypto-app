"""
Módulo de Esteganografia — LSB (Least Significant Bit).

Oculta mensagens de texto ou arquivos inteiros dentro de imagens PNG,
alterando o bit menos significativo dos canais de cor de cada pixel.
"""

import os
import struct
from PIL import Image
import numpy as np


# ─── Constantes ──────────────────────────────────────────────────────────────

MAGIC_TEXT = b"STEG_TXT"      # Marcador para mensagens de texto
MAGIC_FILE = b"STEG_FIL"      # Marcador para arquivos
HEADER_SIZE = 8 + 4           # magic (8 bytes) + length (4 bytes) = 12 bytes
BITS_PER_BYTE = 8


# ─── Funções auxiliares ─────────────────────────────────────────────────────

def _get_capacity(image: Image.Image) -> int:
    """Retorna a capacidade máxima de dados (em bytes) que a imagem pode armazenar."""
    width, height = image.size
    channels = len(image.getbands())
    total_bits = width * height * channels
    # Reservar espaço para o header
    return (total_bits // BITS_PER_BYTE) - HEADER_SIZE


def _data_to_bits(data: bytes) -> np.ndarray:
    """Converte bytes em um array NumPy de bits (Vetorizado)."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    """Converte um array NumPy de bits de volta para bytes."""
    return np.packbits(bits).tobytes()


def _embed_bits(image: Image.Image, bits: np.ndarray) -> Image.Image:
    """Embute bits nos LSBs da imagem utilizando NumPy vetorial para evitar travamento da thread (GIL)."""
    pixels = np.array(image)
    flat = pixels.flatten()

    if len(bits) > len(flat):
        raise ValueError(
            f"Dados muito grandes para esta imagem. "
            f"Capacidade: {len(flat)} bits, Necessário: {len(bits)} bits."
        )

    flat[:len(bits)] = (flat[:len(bits)] & 0xFE) | bits

    modified = flat.reshape(pixels.shape)
    return Image.fromarray(modified.astype(np.uint8))


def _extract_bits(image: Image.Image, num_bits: int) -> np.ndarray:
    """Extrai os LSBs dos pixels da imagem utilizando processos vetorizados do NumPy."""
    pixels = np.array(image)
    flat = pixels.flatten()
    return flat[:num_bits] & 1


# ─── API Pública — Mensagens de texto ───────────────────────────────────────

def hide_message(image_path: str, message: str, output_path: str) -> dict:
    """
    Oculta uma mensagem de texto em uma imagem PNG.

    Args:
        image_path: Caminho da imagem de cobertura.
        message: Mensagem a ser ocultada.
        output_path: Caminho de saída para a imagem esteganografada.

    Returns:
        Dicionário com metadados da operação.
    """
    image = Image.open(image_path).convert("RGB")
    capacity = _get_capacity(image)
    msg_bytes = message.encode("utf-8")

    if len(msg_bytes) > capacity:
        raise ValueError(
            f"Mensagem muito grande. Capacidade: {capacity} bytes, "
            f"Mensagem: {len(msg_bytes)} bytes."
        )

    # Montar header: MAGIC + tamanho
    header = MAGIC_TEXT + struct.pack(">I", len(msg_bytes))
    payload = header + msg_bytes

    bits = _data_to_bits(payload)
    result_image = _embed_bits(image, bits)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    result_image.save(output_path, "PNG")

    img_size = os.path.getsize(image_path)
    return {
        "input_file": image_path,
        "output_file": output_path,
        "file_size_bytes": img_size,
        "key_info": f"LSB, capacidade={capacity} bytes",
        "details": f"Mensagem de {len(msg_bytes)} bytes ocultada com sucesso.",
    }


def reveal_message(image_path: str) -> dict:
    """
    Extrai uma mensagem de texto oculta em uma imagem PNG.

    Returns:
        Dicionário com metadados e a mensagem em 'message'.
    """
    image = Image.open(image_path).convert("RGB")

    # Ler o header primeiro
    header_bits = _extract_bits(image, HEADER_SIZE * BITS_PER_BYTE)
    header_bytes = _bits_to_bytes(header_bits)

    magic = header_bytes[:8]
    if magic != MAGIC_TEXT:
        raise ValueError("Nenhuma mensagem de texto encontrada nesta imagem.")

    msg_len = struct.unpack(">I", header_bytes[8:12])[0]

    # Ler a mensagem completa
    total_bits = (HEADER_SIZE + msg_len) * BITS_PER_BYTE
    all_bits = _extract_bits(image, total_bits)
    all_bytes = _bits_to_bytes(all_bits)

    message = all_bytes[HEADER_SIZE:HEADER_SIZE + msg_len].decode("utf-8")

    img_size = os.path.getsize(image_path)
    return {
        "input_file": image_path,
        "output_file": "",
        "file_size_bytes": img_size,
        "message": message,
        "details": f"Mensagem de {msg_len} bytes extraída com sucesso.",
    }


# ─── API Pública — Arquivos ─────────────────────────────────────────────────

def hide_file(image_path: str, file_path: str, output_path: str) -> dict:
    """
    Oculta um arquivo inteiro dentro de uma imagem PNG.

    O nome original do arquivo é preservado no payload para restauração.

    Args:
        image_path: Caminho da imagem de cobertura.
        file_path: Caminho do arquivo a ser ocultado.
        output_path: Caminho para a imagem esteganografada.

    Returns:
        Dicionário com metadados da operação.
    """
    image = Image.open(image_path).convert("RGB")
    capacity = _get_capacity(image)

    with open(file_path, "rb") as f:
        file_data = f.read()

    # Guardar o nome do arquivo original
    filename = os.path.basename(file_path).encode("utf-8")
    filename_len = len(filename)

    # Payload: MAGIC + file_data_len(4) + filename_len(2) + filename + file_data
    payload_data = (
        struct.pack(">I", len(file_data))
        + struct.pack(">H", filename_len)
        + filename
        + file_data
    )

    total_payload = MAGIC_FILE + struct.pack(">I", len(payload_data)) + payload_data

    data_size = len(total_payload) - HEADER_SIZE
    if data_size > capacity:
        raise ValueError(
            f"Arquivo muito grande para esta imagem. "
            f"Capacidade: {capacity} bytes, Arquivo: {data_size} bytes."
        )

    bits = _data_to_bits(total_payload)
    result_image = _embed_bits(image, bits)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    result_image.save(output_path, "PNG")

    file_size = os.path.getsize(file_path)
    return {
        "input_file": image_path,
        "output_file": output_path,
        "file_size_bytes": file_size,
        "key_info": f"LSB, capacidade={capacity} bytes",
        "details": (
            f"Arquivo '{os.path.basename(file_path)}' ({file_size} bytes) "
            f"ocultado com sucesso na imagem."
        ),
    }


def reveal_file(image_path: str, output_dir: str) -> dict:
    """
    Extrai um arquivo oculto de uma imagem PNG.

    Args:
        image_path: Caminho da imagem esteganografada.
        output_dir: Diretório onde o arquivo extraído será salvo.

    Returns:
        Dicionário com metadados e o caminho do arquivo extraído.
    """
    image = Image.open(image_path).convert("RGB")

    # Ler o header
    header_bits = _extract_bits(image, HEADER_SIZE * BITS_PER_BYTE)
    header_bytes = _bits_to_bytes(header_bits)

    magic = header_bytes[:8]
    if magic != MAGIC_FILE:
        raise ValueError("Nenhum arquivo oculto encontrado nesta imagem.")

    payload_len = struct.unpack(">I", header_bytes[8:12])[0]

    # Ler o payload completo
    total_bits = (HEADER_SIZE + payload_len) * BITS_PER_BYTE
    all_bits = _extract_bits(image, total_bits)
    all_bytes = _bits_to_bytes(all_bits)

    payload = all_bytes[HEADER_SIZE:HEADER_SIZE + payload_len]

    # Parsear payload
    file_data_len = struct.unpack(">I", payload[0:4])[0]
    filename_len = struct.unpack(">H", payload[4:6])[0]
    filename = payload[6:6 + filename_len].decode("utf-8")
    file_data = payload[6 + filename_len:6 + filename_len + file_data_len]

    # Salvar arquivo
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "wb") as f:
        f.write(file_data)

    img_size = os.path.getsize(image_path)
    return {
        "input_file": image_path,
        "output_file": output_path,
        "file_size_bytes": img_size,
        "details": f"Arquivo '{filename}' ({file_data_len} bytes) extraído com sucesso.",
    }


def get_image_capacity(image_path: str) -> int:
    """Retorna a capacidade de dados (bytes) de uma imagem."""
    image = Image.open(image_path).convert("RGB")
    return _get_capacity(image)
