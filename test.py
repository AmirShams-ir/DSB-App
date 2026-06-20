import json
import os
import tempfile
import unittest

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from crypto_utils import decrypt_seed, derive_key, encrypt_seed


class CryptoUtilsTests(unittest.TestCase):
    password = "Strong-Test-Password!42"
    seed_text = "abandon|ability|able|about|" + "|".join(
        f"word-{index}" for index in range(20)
    )

    def test_binary_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            filepath = os.path.join(directory, "seed.bin")
            encrypt_seed(self.seed_text, self.password, filepath)

            with open(filepath, "rb") as file:
                blob = file.read()

            self.assertFalse(blob.startswith(b"{"))
            self.assertNotIn(b"algorithm", blob)
            self.assertNotIn(self.seed_text.encode("utf-8"), blob)
            self.assertEqual(
                decrypt_seed(self.password, filepath),
                self.seed_text,
            )

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            filepath = os.path.join(directory, "seed.bin")
            encrypt_seed(self.seed_text, self.password, filepath)

            with open(filepath, "rb") as file:
                blob = bytearray(file.read())

            blob[-1] ^= 1
            with open(filepath, "wb") as file:
                file.write(blob)

            with self.assertRaisesRegex(
                ValueError,
                "Wrong password or damaged backup",
            ):
                decrypt_seed(self.password, filepath)

    def test_legacy_json_can_still_be_read(self):
        with tempfile.TemporaryDirectory() as directory:
            filepath = os.path.join(directory, "seed.dsb")
            salt = os.urandom(16)
            nonce = os.urandom(12)
            key = derive_key(self.password, salt)
            ciphertext = AESGCM(key).encrypt(
                nonce,
                self.seed_text.encode("utf-8"),
                None,
            )

            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "version": 1,
                        "algorithm": "AES-256-GCM",
                        "kdf": "Argon2id",
                        "salt": salt.hex(),
                        "nonce": nonce.hex(),
                        "ciphertext": ciphertext.hex(),
                    },
                    file,
                )

            self.assertEqual(
                decrypt_seed(self.password, filepath),
                self.seed_text,
            )


if __name__ == "__main__":
    unittest.main()
