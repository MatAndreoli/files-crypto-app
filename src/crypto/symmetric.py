"""
Módulo de criptografia simétrica — AES-256.

Implementa cifragem e decifragem com AES-256 nos modos CBC e GCM,
com derivação de chave via PBKDF2.
"""

import os
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


# ─── Constantes ──────────────────────────────────────────────────────────────

AES_KEY_SIZE = 32        # 256 bits
AES_BLOCK_SIZE = 128     # bits (para padding PKCS7)
IV_SIZE = 16             # 128 bits
GCM_NONCE_SIZE = 12      # 96 bits (recomendado para GCM)
GCM_TAG_SIZE = 16        # 128 bits
SALT_SIZE = 16           # 128 bits
PBKDF2_ITERATIONS = 600_000
CHUNK_SIZE = 64 * 1024   # 64 KB para leitura em blocos


# ─── Geração de chaves ──────────────────────────────────────────────────────

def generate_aes_key() -> bytes:
    """Gera uma chave AES-256 aleatória (32 bytes)."""
    return secrets.token_bytes(AES_KEY_SIZE)


def derive_key_from_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """
    Deriva uma chave AES-256 a partir de uma senha usando PBKDF2-HMAC-SHA256.

    Args:
        password: Senha do usuário.
        salt: Salt opcional; se None, um novo salt é gerado.

    Returns:
        Tupla (key, salt).
    """
    if salt is None:
        salt = secrets.token_bytes(SALT_SIZE)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    key = kdf.derive(password.encode("utf-8"))
    return key, salt


def save_key_to_file(key: bytes, filepath: str) -> str:
    """Salva uma chave AES em arquivo binário."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(key)
    return filepath


def load_key_from_file(filepath: str) -> bytes:
    """Carrega uma chave AES de um arquivo binário."""
    with open(filepath, "rb") as f:
        return f.read()


# ─── AES-256-CBC ─────────────────────────────────────────────────────────────

def encrypt_aes_cbc(input_path: str, output_path: str, key: bytes) -> dict:
    """
    Cifra um arquivo com AES-256-CBC.

    Formato do arquivo de saída: [IV (16 bytes)] [ciphertext com padding PKCS7]

    Returns:
        Dicionário com metadados da operação.
    """
    iv = secrets.token_bytes(IV_SIZE)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(AES_BLOCK_SIZE).padder()

    file_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        fout.write(iv)
        while True:
            chunk = fin.read(CHUNK_SIZE)
            if not chunk:
                break
            padded = padder.update(chunk)
            fout.write(encryptor.update(padded))

        padded = padder.finalize()
        fout.write(encryptor.update(padded))
        fout.write(encryptor.finalize())

    return {
        "input_file": input_path,
        "output_file": output_path,
        "file_size_bytes": file_size,
        "key_info": f"AES-256-CBC, IV={iv.hex()[:16]}...",
        "details": f"Cifrado com sucesso. Tamanho original: {file_size} bytes.",
    }


def decrypt_aes_cbc(input_path: str, output_path: str, key: bytes) -> dict:
    """
    Decifra um arquivo cifrado com AES-256-CBC.

    Espera o formato: [IV (16 bytes)] [ciphertext com padding PKCS7]

    Returns:
        Dicionário com metadados da operação.
    """
    file_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(input_path, "rb") as fin:
        iv = fin.read(IV_SIZE)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(AES_BLOCK_SIZE).unpadder()

        with open(output_path, "wb") as fout:
            while True:
                chunk = fin.read(CHUNK_SIZE)
                if not chunk:
                    break
                decrypted = decryptor.update(chunk)
                fout.write(unpadder.update(decrypted))

            decrypted = decryptor.finalize()
            fout.write(unpadder.update(decrypted))
            fout.write(unpadder.finalize())

    output_size = os.path.getsize(output_path)
    return {
        "input_file": input_path,
        "output_file": output_path,
        "file_size_bytes": file_size,
        "key_info": "AES-256-CBC",
        "details": f"Decifrado com sucesso. Tamanho restaurado: {output_size} bytes.",
    }


# ─── AES-256-GCM ─────────────────────────────────────────────────────────────

def encrypt_aes_gcm(input_path: str, output_path: str, key: bytes) -> dict:
    """
    Cifra um arquivo com AES-256-GCM (autenticado).

    Formato: [nonce (12 bytes)] [tag (16 bytes)] [ciphertext]
    Nota: GCM lê o arquivo inteiro na memória para gerar o tag de autenticação.

    Returns:
        Dicionário com metadados da operação.
    """
    nonce = secrets.token_bytes(GCM_NONCE_SIZE)
    file_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(input_path, "rb") as fin:
        plaintext = fin.read()

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    tag = encryptor.tag

    with open(output_path, "wb") as fout:
        fout.write(nonce)
        fout.write(tag)
        fout.write(ciphertext)

    return {
        "input_file": input_path,
        "output_file": output_path,
        "file_size_bytes": file_size,
        "key_info": f"AES-256-GCM, nonce={nonce.hex()[:12]}...",
        "details": f"Cifrado com autenticação GCM. Tamanho original: {file_size} bytes.",
    }


def decrypt_aes_gcm(input_path: str, output_path: str, key: bytes) -> dict:
    """
    Decifra um arquivo cifrado com AES-256-GCM.

    Espera o formato: [nonce (12 bytes)] [tag (16 bytes)] [ciphertext]

    Returns:
        Dicionário com metadados da operação.
    """
    file_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(input_path, "rb") as fin:
        nonce = fin.read(GCM_NONCE_SIZE)
        tag = fin.read(GCM_TAG_SIZE)
        ciphertext = fin.read()

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    with open(output_path, "wb") as fout:
        fout.write(plaintext)

    output_size = os.path.getsize(output_path)
    return {
        "input_file": input_path,
        "output_file": output_path,
        "file_size_bytes": file_size,
        "key_info": "AES-256-GCM",
        "details": f"Decifrado e autenticado com sucesso. Tamanho restaurado: {output_size} bytes.",
    }
