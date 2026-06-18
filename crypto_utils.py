import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type


def derive_key(password: str, salt: bytes):

    return hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=2,
        hash_len=32,
        type=Type.ID,
    )


def encrypt_seed(seed_text: str, password: str, filepath: str):

    salt = os.urandom(16)

    key = derive_key(password, salt)

    aes = AESGCM(key)

    nonce = os.urandom(12)

    ciphertext = aes.encrypt(
        nonce,
        seed_text.encode(),
        None,
    )

    data = {
        "version": 1,
        "algorithm": "AES-256-GCM",
        "kdf": "Argon2id",
        "salt": salt.hex(),
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
    }

    with open(filepath, "w") as f:
        json.dump(data, f)


def decrypt_seed(password: str, filepath: str):

    with open(filepath, "r") as f:
        data = json.load(f)

    salt = bytes.fromhex(data["salt"])
    nonce = bytes.fromhex(data["nonce"])
    ciphertext = bytes.fromhex(data["ciphertext"])

    key = derive_key(password, salt)

    aes = AESGCM(key)

    plaintext = aes.decrypt(
        nonce,
        ciphertext,
        None,
    )

    return plaintext.decode()