"""Диалог создания и редактирования операции."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk

from ..categories import CategoryStore
from ..dto import TransactionRow
from ..models import KIND_EXPENSE, KIND_INCOME
from ..repository import FinanceService
from ..settings import KIND_LABELS
from ..utils import format_amount, format_date, parse_amount, parse_date
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


class TransactionDialog(tk.Toplevel):
    """Модальное окно для добавления или изменения операции."""

    def __init__(
        self,
        master: tk.Misc,
        service: FinanceService,
        categories: CategoryStore,
        transaction: TransactionRow | None = None,
        default_kind: str = KIND_EXPENSE,
    ) -> None:
        super().__init__(master)
        self.service = service
        self.categories = categories
        self.transaction = transaction
        self.saved = False
        self.transaction_id = transaction.id if transaction else None
        self._category_ids: dict[str, int] = {}

        kind = transaction.kind if transaction else default_kind
        self.kind_var = tk.StringVar(value=kind)
        self.category_var = tk.StringVar(value=transaction.category_name if transaction else "")
        self.amount_var = tk.StringVar(
            value=format_amount(transaction.amount) if transaction else ""
        )
        self.date_var = tk.StringVar(
            value=format_date(transaction.occurred_on) if transaction else format_date(date.today())
        )
        self.comment_var = tk.StringVar(value=transaction.comment if transaction else "")
        self.error_var = tk.StringVar()

        self.title("Редактирование операции" if transaction else "Новая операция")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(master)
        self._build()
        self._reload_categories()
        self._center(master)
        self.grab_set()
        self.amount_entry.focus_set()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())

    # ------------------------------------------------------------------
    def _build(self) -> None:
        card = tk.Frame(
            self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)
        card.columnconfigure(1, weight=1)
        self.card = card

        tk.Label(
            card,
            text="Редактирование операции" if self.transaction else "Новая операция",
            bg=SURFACE,
            fg=TEXT,
            font=(FONT_FAMILY, 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 0))
        tk.Label(
            card,
            text="Заполните поля и нажмите «Сохранить»",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_SMALL,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 6))

        self._label("Тип", 2)
        kind_frame = tk.Frame(card, bg=SURFACE)
        kind_frame.grid(row=2, column=1, sticky="w", pady=(10, 0), padx=(0, 18))
        for code in (KIND_EXPENSE, KIND_INCOME):
            ttk.Radiobutton(
                kind_frame,
                text=KIND_LABELS[code],
                value=code,
                variable=self.kind_var,
                style="Card.TRadiobutton",
                command=self._reload_categories,
            ).pack(side="left", padx=(0, 16))

        self._label("Категория", 3)
        self.category_combo = ttk.Combobox(
            card,
            textvariable=self.category_var,
            state="readonly",
            width=28,
        )
        self.category_combo.grid(
            row=3, column=1, sticky="ew", padx=(0, 18), pady=(10, 0)
        )

        self._label("Сумма", 4)
        self.amount_entry = ttk.Entry(
            card,
            textvariable=self.amount_var,
            font=(FONT_FAMILY, 14, "bold"),
            justify="right",
        )
        self.amount_entry.grid(row=4, column=1, sticky="ew", padx=(0, 18), pady=(10, 0))

        self._label("Дата", 5)
        date_frame = tk.Frame(card, bg=SURFACE)
        date_frame.grid(row=5, column=1, sticky="w", pady=(10, 0), padx=(0, 18))
        ttk.Entry(date_frame, textvariable=self.date_var, width=14).pack(side="left")
        ttk.Button(
            date_frame,
            text="Сегодня",
            command=lambda: self.date_var.set(format_date(date.today())),
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            date_frame, text="ДД.ММ.ГГГГ", bg=SURFACE, fg=MUTED, font=FONT_SMALL
        ).pack(side="left", padx=(8, 0))

        self._label("Комментарий", 6)
        ttk.Entry(card, textvariable=self.comment_var, width=30).grid(
            row=6, column=1, sticky="ew", padx=(0, 18), pady=(10, 0)
        )

        tk.Label(
            card,
            textvariable=self.error_var,
            bg=SURFACE,
            fg=EXPENSE,
            font=FONT_SMALL,
            wraplength=360,
            justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=18, pady=(10, 0))

        buttons = tk.Frame(card, bg=SURFACE)
        buttons.grid(row=8, column=0, columnspan=2, sticky="e", padx=18, pady=(12, 16))
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            buttons, text="Сохранить", style="Accent.TButton", command=self._save
        ).pack(side="left")

    def _label(self, text: str, row: int) -> None:
        tk.Label(
            self.card,
            text=text,
            bg=SURFACE,
            fg=MUTED,
            font=FONT_SMALL,
        ).grid(row=row, column=0, sticky="w", padx=(18, 12), pady=(10, 0))

    def _reload_categories(self) -> None:
        kind = self.kind_var.get()
        self._category_ids = {
            item.name: item.id for item in self.categories.all(kind)
        }
        values = list(self._category_ids)
        self.category_combo.configure(values=values)
        if self.category_var.get() not in self._category_ids:
            self.category_var.set(values[0] if values else "")
        if values:
            if self.error_var.get().startswith("Для этого типа"):
                self.error_var.set("")
        else:
            self.error_var.set(
                "Для этого типа пока нет категорий — добавьте её на вкладке «Категории»."
            )

    def _save(self) -> None:
        try:
            amount = parse_amount(self.amount_var.get())
            occurred_on = parse_date(self.date_var.get())
        except ValueError as exc:
            self.error_var.set(str(exc))
            return

        category_id = self._category_ids.get(self.category_var.get())
        if category_id is None:
            self.error_var.set("Выберите категорию")
            return

        try:
            if self.transaction_id is None:
                self.transaction_id = self.service.add_transaction(
                    category_id=category_id,
                    amount=amount,
                    occurred_on=occurred_on,
                    comment=self.comment_var.get(),
                )
            else:
                self.service.update_transaction(
                    transaction_id=self.transaction_id,
                    category_id=category_id,
                    amount=amount,
                    occurred_on=occurred_on,
                    comment=self.comment_var.get(),
                )
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
