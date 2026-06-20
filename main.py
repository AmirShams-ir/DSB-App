import flet as ft
import re

from crypto_utils import encrypt_seed
from crypto_utils import decrypt_seed

def main(page: ft.Page):

    page.title = "DSB"
    page.window.width = 850
    page.window.height = 750
    page.padding = 15

    # ---------------- HOME ----------------

    def show_home(e=None):

        page.clean()

        page.add(
            ft.Column(
                [
                    ft.Text(
                        "Digital Seed Phrase Backup",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Divider(),
                    ft.Button(
                        "Encrypt",
                        width=250,
                        on_click=show_encrypt,
                    ),
                    ft.Button(
                        "Decrypt",
                        width=250,
                        on_click=show_decrypt,
                    ),
                ],
                spacing=20,
            )
        )

        page.update()

    # ---------------- ENCRYPT ----------------

    def show_encrypt(e=None):

        page.clean()

        seed_fields = []

        for i in range(24):
            seed_fields.append(
                ft.TextField(
                    label=f"{i + 1:02d}",
                    width=150,
                )
            )

        seed_fields.append(
            ft.TextField(
                label="25 Optional",
                width=150,
                border_color=ft.Colors.AMBER,
            )
        )

        rows = []

        for i in range(0, 25, 5):
            rows.append(
                ft.Row(
                    seed_fields[i:i + 5],
                    spacing=10,
                )
            )

        destination = ft.TextField(
            label="File Destination",
            value="seed.dsb",
            width=500,
        )

        password = ft.TextField(
            label="Encryption Password",
            password=True,
            can_reveal_password=True,
            width=350,
        )

        strength = ft.Text()

        encrypt_btn = ft.Button(
            "Encrypt",
            disabled=True,
        )

        def validate_password(e):

            pwd = password.value or ""

            checks = [
                len(pwd) >= 12,
                bool(re.search(r"[A-Z]", pwd)),
                bool(re.search(r"[a-z]", pwd)),
                bool(re.search(r"\d", pwd)),
                bool(re.search(r"[^A-Za-z0-9]", pwd)),
            ]

            strength.value = (
                f"{'✓' if checks[0] else '✗'} Length >= 12\n"
                f"{'✓' if checks[1] else '✗'} Uppercase\n"
                f"{'✓' if checks[2] else '✗'} Lowercase\n"
                f"{'✓' if checks[3] else '✗'} Number\n"
                f"{'✓' if checks[4] else '✗'} Symbol"
            )

            encrypt_btn.disabled = not all(checks)

            page.update()

        password.on_change = validate_password

        def do_encrypt(e):

            try:

                words = []

                for field in seed_fields:
                    value = (field.value or "").strip()

                    if value:
                        words.append(value)

                seed_text = "|".join(words)

                encrypt_seed(
                    seed_text,
                    password.value,
                    destination.value,
                )

                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text("Backup encrypted successfully")
                    )
                )

            except Exception as ex:
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text(f"Error: {ex}"),
                        bgcolor=ft.Colors.RED,
                    )
                )
            page.update()

        encrypt_btn.on_click = do_encrypt

        page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                on_click=show_home,
                            ),
                            ft.Text(
                                "Encrypt Seed Phrase",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ]
                    ),
                    ft.Divider(),
                    *rows,
                    ft.Divider(),
                    destination,
                    password,
                    strength,
                    encrypt_btn,
                ],
                spacing=10,
            )
        )

        page.update()

    # ---------------- DECRYPT ----------------
    def show_decrypt(e=None):

        page.clean()

        encrypted_file = ft.TextField(
            label="Encrypted File",
            value="seed.dsb",
            width=500,
        )

        password = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=350,
        )

        result_fields = []

        for i in range(24):
            result_fields.append(
                ft.TextField(
                    label=f"{i + 1:02d}",
                    width=150,
                    read_only=True,
                )
            )

        result_fields.append(
            ft.TextField(
                label="25 Optional",
                width=150,
                read_only=True,
                border_color=ft.Colors.AMBER,
            )
        )

        rows = [
            ft.Row(result_fields[i:i+5], spacing=10)
            for i in range(0, 25, 5)
        ]

        def do_decrypt(e):

            try:

                seed_text = decrypt_seed(
                    password.value,
                    encrypted_file.value,
                )

                words = seed_text.split("|")

                for i in range(min(len(words), 25)):
                    result_fields[i].value = words[i]

                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text("Backup decrypted successfully")
                    )
                )

            except Exception as ex:
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text(f"Error: {ex}"),
                        bgcolor=ft.Colors.RED,
                    )
                )
            page.update()

        page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                on_click=show_home,
                            ),
                            ft.Text(
                                "Decrypt Backup",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ]
                    ),
                    ft.Divider(),
                    encrypted_file,
                    password,
                    ft.Button("Decrypt", on_click=do_decrypt),
                    ft.Divider(),
                    *rows,
                ]
            )
        )

        page.update()

    show_home()


if __name__ == "__main__":
    ft.run(main)