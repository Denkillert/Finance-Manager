"""Диалог создания и переименования категории."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..dto import CategoryInfo
from ..models import KIND_EXPENSE, KIND_INCOME
from ..repository import FinanceService
from ..settings import KIND_LABELS
from .theme import (
    BG,
    BORDER,
    EXPENSE,
    FONT_FAMILY,
    FONT_SMALL,
    MUTED,
    SURFACE,
    TEXT,
)


class CategoryDialog(tk.Toplevel):
    """Модальное окно для добавления или переименования категории."""

    def __init__(
        self,
        master: tk.Misc,
        service: FinanceService,
        category: CategoryInfo | None = None,
        default_kind: str = KIND_EXPENSE,
    ) -> None:
        super().__init__(master)
        self.service = service
        self.category = category
        self.saved = False

        self.name_var = tk.StringVar(value=category.name if category else "")
        self.kind_var = tk.StringVar(
            value=category.kind if category else default_kind
        )
        self.error_var = tk.StringVar()

        self.title("Переименование категории" if category else "Новая категория")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(master)
        self._build()
        self._center(master)
        self.grab_set()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())
        self.name_entry.focus_set()
        self.name_entry.select_range(0, "end")

    def _build(self) -> None:
        card = tk.Frame(
            self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)
        card.columnconfigure(1, weight=1)
        self.card = card

        tk.Label(
            card,
            text="Переименование категории" if self.category else "Новая категория",
            bg=SURFACE,
            fg=TEXT,
            font=(FONT_FAMILY, 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 4))

        tk.Label(
            card, text="Вид операции", bg=SURFACE, fg=MUTED, font=FONT_SMALL
        ).grid(row=1, column=0, sticky="w", padx=(18, 12), pady=(12, 0))
        kind_frame = tk.Frame(card, bg=SURFACE)
        kind_frame.grid(row=1, column=1, sticky="w", padx=(0, 18), pady=(12, 0))
        state = "disabled" if self.category else "normal"
        for code in (KIND_EXPENSE, KIND_INCOME):
            ttk.Radiobutton(
                kind_frame,
                text=KIND_LABELS[code],
                value=code,
                variable=self.kind_var,
                style="Card.TRadiobutton",
                state=state,
            ).pack(side="left", padx=(0, 16))

        tk.Label(
            card, text="Название", bg=SURFACE, fg=MUTED, font=FONT_SMALL
        ).grid(row=2, column=0, sticky="w", padx=(18, 12), pady=(14, 0))
        self.name_entry = ttk.Entry(card, textvariable=self.name_var, width=30)
        self.name_entry.grid(row=2, column=1, sticky="ew", padx=(0, 18), pady=(14, 0))

        tk.Label(
            card,
            textvariable=self.error_var,
            bg=SURFACE,
            fg=EXPENSE,
            font=FONT_SMALL,
            wraplength=320,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(10, 0))

        buttons = tk.Frame(card, bg=SURFACE)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", padx=18, pady=(14, 16))
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            buttons, text="Сохранить", style="Accent.TButton", command=self._save
        ).pack(side="left")

    def _save(self) -> None:
        try:
            if self.category is None:
                self.service.add_category(self.name_var.get(), self.kind_var.get())
            else:
                self.service.rename_category(self.category.id, self.name_var.get())
        except ValueError as exc:
            self.error_var.set(str(exc))
            return
        self.saved = True
        self.destroy()

    def _center(self, master: tk.Misc) -> None:
        self.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - width) // 2
        y = master.winfo_rooty() + (master.winfo_height() - height) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
