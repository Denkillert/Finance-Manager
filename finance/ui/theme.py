"""Цвета, шрифты и стили ttk для всего приложения."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

BG = "#F3F5FA"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FAFC"
BORDER = "#E2E8F0"
TEXT = "#1E293B"
MUTED = "#64748B"
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
INCOME = "#15803D"
EXPENSE = "#B91C1C"
SELECTION = "#DBEAFE"

FONT_FAMILY = "Segoe UI"
FONT_BASE = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_SMALL_BOLD = (FONT_FAMILY, 9, "bold")
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_TITLE = (FONT_FAMILY, 16, "bold")


def configure_theme(root: tk.Misc) -> ttk.Style:
    """Настраивает тему ``clam`` под оформление приложения."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:  # pragma: no cover - тема есть в стандартной сборке
        pass

    root.option_add("*Font", FONT_BASE)
    root.option_add("*TCombobox*Listbox.font", FONT_BASE)

    style.configure(".", font=FONT_BASE, background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)

    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT_SMALL)
    style.configure("HeaderTitle.TLabel", background=SURFACE, font=FONT_TITLE)
    style.configure("HeaderSubtitle.TLabel", background=SURFACE, foreground=MUTED, font=FONT_SMALL)
    style.configure("SectionTitle.TLabel", background=SURFACE, font=FONT_BOLD)
    style.configure("CardTitle.TLabel", background=SURFACE, foreground=MUTED, font=FONT_SMALL)
    style.configure("CardValue.TLabel", background=SURFACE, font=(FONT_FAMILY, 20, "bold"))
    style.configure("CardHint.TLabel", background=SURFACE, foreground=MUTED, font=FONT_SMALL)

    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure(
        "TNotebook.Tab",
        background=BG,
        foreground=MUTED,
        padding=(18, 9),
        font=FONT_BASE,
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", SURFACE)],
        foreground=[("selected", ACCENT)],
        expand=[("selected", (0, 0, 0, 0))],
    )

    style.configure(
        "TButton",
        font=FONT_BASE,
        padding=(12, 7),
        background=SURFACE,
        bordercolor=BORDER,
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", "#EEF2F9"), ("pressed", "#E2E8F0")],
        bordercolor=[("focus", ACCENT)],
    )
    style.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT)
    style.map(
        "Accent.TButton",
        background=[("active", ACCENT_HOVER), ("pressed", "#1E40AF"), ("disabled", "#93B4F5")],
        foreground=[("disabled", "#F1F5F9")],
    )
    style.configure("Danger.TButton", foreground=EXPENSE, background=SURFACE)
    style.map("Danger.TButton", background=[("active", "#FEF2F2")])

    style.configure("TEntry", padding=6, fieldbackground=SURFACE, bordercolor=BORDER)
    style.map(
        "TEntry",
        bordercolor=[("focus", ACCENT)],
        fieldbackground=[("disabled", "#F1F5F9")],
    )
    style.configure(
        "TCombobox",
        padding=6,
        fieldbackground=SURFACE,
        bordercolor=BORDER,
        arrowcolor=MUTED,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", SURFACE), ("disabled", "#F1F5F9")],
        bordercolor=[("focus", ACCENT)],
        selectbackground=[("readonly", SURFACE)],
        selectforeground=[("readonly", TEXT)],
    )

    style.configure(
        "Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        rowheight=30,
        borderwidth=0,
        font=FONT_BASE,
    )
    style.configure(
        "Treeview.Heading",
        background="#F1F5F9",
        foreground=MUTED,
        font=FONT_SMALL_BOLD,
        relief="flat",
        padding=(10, 8),
    )
    style.map("Treeview.Heading", background=[("active", "#E2E8F0")])
    style.map(
        "Treeview",
        background=[("selected", SELECTION)],
        foreground=[("selected", TEXT)],
    )
    style.configure(
        "Vertical.TScrollbar",
        background="#CBD5E1",
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=MUTED,
    )
    style.configure("Card.TRadiobutton", background=SURFACE, foreground=TEXT)
    style.map("Card.TRadiobutton", background=[("active", SURFACE)])
    return style
