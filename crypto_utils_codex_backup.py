import json
import os
import struct
import tempfile
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# Binary format v2:
# magic | version | flags | salt | nonce | ciphertext length | ciphertext
#
# Algorithm names and KDF settings are intentionally not stored in the backup.
# The whole header is authenticated as AES-GCM associated data.
_MAGIC = b"\xD5\x42\x02\xA7"
_FORMAT_VERSION = 2
_FLAGS = 0
_SALT_SIZE = 16
_NONCE_SIZE = 12
_HEADER = struct.Struct(">4sBB16s12sI")
_MIN_PLAINTEXT_SIZE = 512
_PADDING_BLOCK_SIZE = 256
_MAX_CIPHERTEXT_SIZE = 1024 * 1024

_ARGON2_TIME_COST = 3
_ARGON2_MEMORY_COST = 65536
_ARGON2_PARALLELISM = 2


def serialize_seed(words: list[str], passphrase: str = "") -> str:
    if len(words) != 24 or any(not word for word in words):
        raise ValueError("Exactly 24 seed words are required")

    return json.dumps(
        {
            "version": 1,
            "words": words,
            "passphrase": passphrase,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def deserialize_seed(seed_text: str) -> tuple[list[str], str]:
    try:
        data = json.loads(seed_text)
    except json.JSONDecodeError:
        # Compatibility with backups created before structured seed payloads.
        values = seed_text.split("|")
        if len(values) not in (24, 25):
            raise ValueError("Invalid seed payload")
        return values[:24], values[24] if len(values) == 25 else ""

    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Unsupported seed payload")

    words = data.get("words")
    passphrase = data.get("passphrase", "")
    if (
        not isinstance(words, list)
        or len(words) != 24
        or any(not isinstance(word, str) or not word for word in words)
        or not isinstance(passphrase, str)
    ):
        raise ValueError("Invalid seed payload")

    return words, passphrase


def derive_key(password: str, salt: bytes) -> bytes:
    if not password:
        raise ValueError("Password cannot be empty")

    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=_ARGON2_TIME_COST,
        memory_cost=_ARGON2_MEMORY_COST,
        parallelism=_ARGON2_PARALLELISM,
        hash_len=32,
        type=Type.ID,
    )


def _pack_plaintext(seed_text: str) -> bytes:
    seed_bytes = seed_text.encode("utf-8")

    if len(seed_bytes) > 65535:
        raise ValueError("Seed data is too large")

    required_size = 2 + len(seed_bytes)
    padded_size = max(
        _MIN_PLAINTEXT_SIZE,
        ((required_size + _PADDING_BLOCK_SIZE - 1) // _PADDING_BLOCK_SIZE)
        * _PADDING_BLOCK_SIZE,
    )

    return (
        struct.pack(">H", len(seed_bytes))
        + seed_bytes
        + os.urandom(padded_size - required_size)
    )


def _unpack_plaintext(payload: bytes) -> str:
    if len(payload) < 2:
        raise ValueError("Invalid encrypted backup")

    seed_size = struct.unpack(">H", payload[:2])[0]
    if seed_size > len(payload) - 2:
        raise ValueError("Invalid encrypted backup")

    try:
        return payload[2 : 2 + seed_size].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid encrypted backup") from exc


def _atomic_write(filepath: str, data: bytes) -> None:
    destination = Path(filepath).expanduser()
    parent = destination.parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=parent,
    )

    try:
        with os.fdopen(file_descriptor, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, destination)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


def encrypt_seed_to_bytes(seed_text: str, password: str) -> bytes:
    salt = os.urandom(_SALT_SIZE)
    nonce = os.urandom(_NONCE_SIZE)
    key = derive_key(password, salt)
    payload = _pack_plaintext(seed_text)

    ciphertext_size = len(payload) + 16
    header = _HEADER.pack(
        _MAGIC,
        _FORMAT_VERSION,
        _FLAGS,
        salt,
        nonce,
        ciphertext_size,
    )
    ciphertext = AESGCM(key).encrypt(nonce, payload, header)

    return header + ciphertext


def encrypt_seed(seed_text: str, password: str, filepath: str) -> None:
    _atomic_write(filepath, encrypt_seed_to_bytes(seed_text, password))


def _decrypt_binary(password: str, blob: bytes) -> str:
    if len(blob) < _HEADER.size:
        raise ValueError("Invalid encrypted backup")

    magic, version, flags, salt, nonce, ciphertext_size = _HEADER.unpack(
        blob[: _HEADER.size]
    )

    if magic != _MAGIC or version != _FORMAT_VERSION or flags != _FLAGS:
        raise ValueError("Unsupported encrypted backup format")

    if (
        ciphertext_size < 16
        or ciphertext_size > _MAX_CIPHERTEXT_SIZE
        or len(blob) != _HEADER.size + ciphertext_size
    ):
        raise ValueError("Invalid encrypted backup")

    header = blob[: _HEADER.size]
    ciphertext = blob[_HEADER.size :]
    key = derive_key(password, salt)

    try:
        payload = AESGCM(key).decrypt(nonce, ciphertext, header)
    except InvalidTag as exc:
        raise ValueError("Wrong password or damaged backup") from exc

    return _unpack_plaintext(payload)


def _decrypt_legacy_json(password: str, blob: bytes) -> str:
    try:
        data = json.loads(blob.decode("utf-8"))
        salt = bytes.fromhex(data["salt"])
        nonce = bytes.fromhex(data["nonce"])
        ciphertext = bytes.fromhex(data["ciphertext"])
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid legacy backup") from exc

    key = derive_key(password, salt)

    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except (InvalidTag, UnicodeDecodeError) as exc:
        raise ValueError("Wrong password or damaged backup") from exc


def decrypt_seed_bytes(password: str, blob: bytes) -> str:
    if len(blob) > _HEADER.size + _MAX_CIPHERTEXT_SIZE:
        raise ValueError("Encrypted backup is too large")

    if blob.startswith(_MAGIC):
        return _decrypt_binary(password, blob)

    # Read-only compatibility for backups created by version 1.
    if blob.lstrip().startswith(b"{"):
        return _decrypt_legacy_json(password, blob)

    raise ValueError("Unsupported encrypted backup format")


def decrypt_seed(password: str, filepath: str) -> str:
    with open(filepath, "rb") as file:
        blob = file.read(_HEADER.size + _MAX_CIPHERTEXT_SIZE + 1)

    return decrypt_seed_bytes(password, blob)
