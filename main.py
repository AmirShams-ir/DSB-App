import flet as ft
import re

from crypto_utils import encrypt_seed
from crypto_utils import decrypt_seed
from mnemonic import Mnemonic

mnemo = Mnemonic("english")

def main(page: ft.Page):

    page.title = "DSB"
    page.window.width = 850
    page.window.height = 750
    page.padding = 15
    file_picker = ft.FilePicker()

    # ---------------- HOME ----------------

    def show_home(e=None):

        page.clean()

        page.add(
            ft.Column(
                [
                    ft.Text(
                        "🗝️ Digital Seed Phrase Backup",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Divider(),
                    
                    ft.Text(
                        "🛡️ What is DSB ?",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    
                    ft.Text(
                        "Plain-text seed backups are easy to read, copy, photograph, index, or leak. DSB provides a small desktop/mobile interface for creating an encrypted backup without requiring a remote service or network connection with maximum security.",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Divider(),
                    
                    ft.Text(
                        "Encryption:",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    
                    ft.Text(
                        "Enter your seed pharase  in order, Optionally enter the wallet passphrase, Choose the destination file path, Enter a strong password, Select Encrypt.",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    
                    ft.Button(
                        "🔒Encrypt",
                        width=250,
                        on_click=show_encrypt,
                    ),
                    ft.Divider(),
                    
                    ft.Text(
                        "Decryption:",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    
                    ft.Text(
                        "Select your backup file, Enter the encryption password, Select Decrypt, The recovered seed pharase and passphrase appear in read-only fields.",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    
                    ft.Button(
                        "🔓Decrypt",
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
            value="File path",
            width=500,
        )

        async def choose_destination(e):

            selected_path = await file_picker.save_file(
                dialog_title="Save encrypted backup",
                file_name="seed.bin",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["bin"],
            )

            if selected_path:
                if not selected_path.lower().endswith(".bin"):
                    selected_path += ".bin"

                destination.value = selected_path
                page.update()

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
                output_path = (destination.value or "").strip()

                if not output_path or output_path == "File path":
                    raise ValueError("Please choose a destination file")

                if not output_path.lower().endswith(".bin"):
                    output_path += ".bin"
                    destination.value = output_path

                words = [
                    (field.value or "").strip().lower()
                    for field in seed_fields[:24]
                ]

                mnemonic_phrase = " ".join(words)

                if any(not word for word in words) or not mnemo.check(mnemonic_phrase):
                    page.show_dialog(
                        ft.SnackBar(
                            content=ft.Text("Seed is not Correct"),
                            bgcolor=ft.Colors.RED,
                        )
                    )
                    return

                optional_word = (seed_fields[24].value or "").strip()

                if optional_word:
                    words.append(optional_word)

                seed_text = "|".join(words)

                encrypt_seed(
                    seed_text,
                    password.value,
                    output_path,
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
                    ft.Row(
                        [
                            destination,
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                tooltip="Choose save location",
                                on_click=choose_destination,
                            ),
                        ]
                    ),
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
            value="File path",
            width=500,
        )

        async def choose_encrypted_file(e):

            selected_files = await file_picker.pick_files(
                dialog_title="Open encrypted backup",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["bin", "dsb"],
                allow_multiple=False,
            )

            if selected_files and selected_files[0].path:
                encrypted_file.value = selected_files[0].path
                page.update()

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
                    ft.Row(
                        [
                            encrypted_file,
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                tooltip="Choose encrypted backup",
                                on_click=choose_encrypted_file,
                            ),
                        ]
                    ),
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
