"""
Módulo de criptografia assimétrica — RSA.

Implementa cifragem híbrida: RSA cifra uma chave AES efêmera,
e AES-GCM cifra o conteúdo do arquivo. Isso permite cifrar
arquivos de qualquer tamanho com chave pública RSA.
"""

import os
import secrets
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# ─── Constantes ──────────────────────────────────────────────────────────────

RSA_KEY_SIZE = 2048
AES_KEY_SIZE = 32       # 256 bits
GCM_NONCE_SIZE = 12     # 96 bits
GCM_TAG_SIZE = 16       # 128 bits


# ─── Geração e gerenciamento de chaves RSA ───────────────────────────────────

def generate_rsa_keypair(key_size: int = RSA_KEY_SIZE):
    """
    Gera um par de chaves RSA.

    Returns:
        Tupla (private_key, public_key).
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    return private_key, public_key


def save_private_key(private_key, filepath: str, password: str | None = None) -> str:
    """Salva a chave privada em formato PEM."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

    if password:
        encryption = serialization.BestAvailableEncryption(password.encode("utf-8"))
    else:
        encryption = serialization.NoEncryption()

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    with open(filepath, "wb") as f:
        f.write(pem)
    return filepath


def save_public_key(public_key, filepath: str) -> str:
    """Salva a chave pública em formato PEM."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(filepath, "wb") as f:
        f.write(pem)
    return filepath


def load_private_key(filepath: str, password: str | None = None):
    """Carrega a chave privada de um arquivo PEM."""
    with open(filepath, "rb") as f:
        pem = f.read()
    pwd = password.encode("utf-8") if password else None
    return serialization.load_pem_private_key(pem, password=pwd, backend=default_backend())


def load_public_key(filepath: str):
    """Carrega a chave pública de um arquivo PEM."""
    with open(filepath, "rb") as f:
        pem = f.read()
    return serialization.load_pem_public_key(pem, backend=default_backend())


# ─── Criptografia Híbrida (RSA + AES-GCM) ───────────────────────────────────

def encrypt_rsa(input_path: str, output_path: str, public_key) -> dict:
    """
    Cifra um arquivo usando criptografia híbrida RSA + AES-256-GCM.

    1. Gera uma chave AES-256 efêmera
    2. Cifra a chave AES com RSA-OAEP (chave pública)
    3. Cifra o conteúdo do arquivo com AES-256-GCM

    Formato de saída:
        [2 bytes: tamanho da chave RSA cifrada]
        [chave AES cifrada com RSA]
        [nonce GCM (12 bytes)]
        [tag GCM (16 bytes)]
        [ciphertext AES-GCM]

    Returns:
        Dicionário com metadados da operação.
    """
    file_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # Gerar chave AES efêmera
    aes_key = secrets.token_bytes(AES_KEY_SIZE)
    nonce = secrets.token_bytes(GCM_NONCE_SIZE)

    # Cifrar a chave AES com RSA-OAEP
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Cifrar o conteúdo com AES-GCM
    with open(input_path, "rb") as fin:
        plaintext = fin.read()

    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    tag = encryptor.tag

    # Escrever arquivo de saída
    enc_key_len = len(encrypted_aes_key)
    with open(output_path, "wb") as fout:
        fout.write(enc_key_len.to_bytes(2, "big"))
        fout.write(encrypted_aes_key)
        fout.write(nonce)
        fout.write(tag)
        fout.write(ciphertext)

    key_bits = public_key.key_size
    return {
        "input_file": input_path,
        "output_file": output_path,
        "file_size_bytes": file_size,
        "key_info": f"RSA-{key_bits} + AES-256-GCM (híbrido)",
        "details": f"Cifrado com criptografia híbrida. Tamanho original: {file_size} bytes.",
    }


def decrypt_rsa(input_path: str, output_path: str, private_key) -> dict:
    """
    Decifra um arquivo cifrado com criptografia híbrida RSA + AES-256-GCM.

    Returns:
        Dicionário com metadados da operação.
    """
    file_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(input_path, "rb") as fin:
        enc_key_len = int.from_bytes(fin.read(2), "big")
        encrypted_aes_key = fin.read(enc_key_len)
        nonce = fin.read(GCM_NONCE_SIZE)
        tag = fin.read(GCM_TAG_SIZE)
        ciphertext = fin.read()

    # Decifrar a chave AES com RSA
    aes_key = private_key.decrypt(
        encrypted_aes_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Decifrar o conteúdo com AES-GCM
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    with open(output_path, "wb") as fout:
        fout.write(plaintext)

    key_bits = private_key.key_size
    output_size = os.path.getsize(output_path)
    return {
        "input_file": input_path,
        "output_file": output_path,
        "file_size_bytes": file_size,
        "key_info": f"RSA-{key_bits} + AES-256-GCM (híbrido)",
        "details": f"Decifrado com sucesso. Tamanho restaurado: {output_size} bytes.",
    }
