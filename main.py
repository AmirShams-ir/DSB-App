import flet as ft

def main(page: ft.Page):
    page.title = "DSB"

    page.add(
        ft.Text("Digital Seed Phrase Backup"),
        ft.ElevatedButton("Test")
    )

ft.app(main)