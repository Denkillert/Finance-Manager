"""Главное окно приложения."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from decimal import Decimal
from tkinter import messagebox, ttk

from ..categories import CategoryStore
from ..dto import CategoryInfo, Summary, TransactionRow
from ..models import KIND_EXPENSE, KIND_INCOME
from ..repository import FinanceService, TransactionFilter
from ..settings import (
    APP_NAME,
    APP_VERSION,
    CHART_COLORS,
    KIND_LABELS,
    MIN_WINDOW_SIZE,
    PERIOD_CODES,
    PERIODS,
    WINDOW_SIZE,
)
from ..utils import (
    format_date,
    format_money,
    format_period,
    month_bounds,
    parse_date,
    previous_month_bounds,
    year_bounds,
)
from .category_dialog import CategoryDialog
from .dpi import enable_dpi_awareness
from .theme import (
    BG,
    BORDER,
    EXPENSE,
    FONT_BASE,
    FONT_FAMILY,
    FONT_SMALL,
    INCOME,
    MUTED,
    SURFACE,
    TEXT,
    configure_theme,
)
from .transaction_dialog import TransactionDialog

ALL_KINDS = "Все операции"
ALL_CATEGORIES = "Все категории"
ZERO = Decimal("0.00")


class FinanceApp(tk.Tk):
    """Главное окно: сводка, операции, категории и аналитика."""

    def __init__(self, service: FinanceService) -> None:
        enable_dpi_awareness()
        super().__init__()
        self.service = service
        self.store = CategoryStore()
        self._rows: list[TransactionRow] = []
        self._categories: list[CategoryInfo] = []
        self._chart_rows: list[tuple[str, Decimal]] = []
        self._income_rows: list[tuple[str, Decimal]] = []
        self._category_options: dict[str, int] = {}
        self._kind_labels = {ALL_KINDS: None}
        self._kind_labels.update({label: code for code, label in KIND_LABELS.items()})
        self._search_job: str | None = None

        self.title(APP_NAME)
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.minsize(*MIN_WINDOW_SIZE)
        self.configure(bg=BG)
        configure_theme(self)
        self._build_variables()
        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()
        self._sync_date_entries()
        self._center()
        self.reload_all()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_variables(self) -> None:
        self.period_var = tk.StringVar(value=PERIODS[0][0])
        self.kind_var = tk.StringVar(value=ALL_KINDS)
        self.category_var = tk.StringVar(value=ALL_CATEGORIES)
        self.search_var = tk.StringVar()
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()

        self.balance_var = tk.StringVar(value="0 ₽")
        self.income_var = tk.StringVar(value="0 ₽")
        self.expense_var = tk.StringVar(value="0 ₽")
        self.card_hint_var = tk.StringVar(value="")
        self.footer_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.analytics_period_var = tk.StringVar(value="")
        self.income_total_var = tk.StringVar(value="")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Обновить", accelerator="F5", command=self.reload_all)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.destroy)
        menubar.add_cascade(label="Файл", menu=file_menu)

        op_menu = tk.Menu(menubar, tearoff=0)
        op_menu.add_command(
            label="Добавить расход",
            accelerator="Ctrl+N",
            command=lambda: self.add_transaction(KIND_EXPENSE),
        )
        op_menu.add_command(
            label="Добавить доход", command=lambda: self.add_transaction(KIND_INCOME)
        )
        op_menu.add_separator()
        op_menu.add_command(
            label="Категории", command=lambda: self.notebook.select(self.tab_categories)
        )
        menubar.add_cascade(label="Операции", menu=op_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)
        self.configure(menu=menubar)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build_header()
        self._build_cards()
        self._build_notebook()
        self._build_statusbar()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=SURFACE)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        inner = tk.Frame(header, bg=SURFACE)
        inner.grid(row=0, column=0, sticky="ew", padx=22, pady=14)
        inner.columnconfigure(0, weight=1)

        titles = tk.Frame(inner, bg=SURFACE)
        titles.grid(row=0, column=0, sticky="w")
        tk.Label(
            titles, text=APP_NAME, bg=SURFACE, fg=TEXT, font=(FONT_FAMILY, 16, "bold")
        ).pack(anchor="w")
        tk.Label(
            titles,
            text="Tkinter + SQLAlchemy · база данных SQLite",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_SMALL,
        ).pack(anchor="w")

        actions = tk.Frame(inner, bg=SURFACE)
        actions.grid(row=0, column=1, sticky="e")
        ttk.Button(
            actions,
            text="+  Добавить операцию",
            style="Accent.TButton",
            command=self.add_transaction,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Обновить", command=self.reload_all).pack(side="left")

        tk.Frame(header, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew")

    def _build_cards(self) -> None:
        cards = tk.Frame(self, bg=BG)
        cards.grid(row=1, column=0, sticky="ew", padx=22, pady=(16, 0))
        for column in range(3):
            cards.columnconfigure(column, weight=1, uniform="cards")
        _, self.balance_label = self._make_card(
            cards, 0, "Баланс за период", self.balance_var, TEXT
        )
        self._make_card(cards, 1, "Доходы", self.income_var, INCOME)
        self._make_card(cards, 2, "Расходы", self.expense_var, EXPENSE)

    def _make_card(
        self,
        parent: tk.Misc,
        column: int,
        title: str,
        variable: tk.StringVar,
        color: str,
    ) -> tuple[tk.Frame, ttk.Label]:
        frame = tk.Frame(
            parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        frame.grid(
            row=0, column=column, sticky="ew", padx=(0 if column == 0 else 12, 0)
        )
        ttk.Label(frame, text=title, style="CardTitle.TLabel").pack(
            anchor="w", padx=16, pady=(12, 0)
        )
        value = ttk.Label(
            frame, textvariable=variable, style="CardValue.TLabel", foreground=color
        )
        value.pack(anchor="w", padx=16, pady=(2, 0))
        ttk.Label(frame, textvariable=self.card_hint_var, style="CardHint.TLabel").pack(
            anchor="w", padx=16, pady=(0, 12)
        )
        return frame, value

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=22, pady=(16, 0))
        self.tab_transactions = ttk.Frame(self.notebook, padding=14)
        self.tab_categories = ttk.Frame(self.notebook, padding=14)
        self.tab_analytics = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.tab_transactions, text="Операции")
        self.notebook.add(self.tab_categories, text="Категории")
        self.notebook.add(self.tab_analytics, text="Аналитика")
        self._build_transactions_tab()
        self._build_categories_tab()
        self._build_analytics_tab()

    def _build_transactions_tab(self) -> None:
        tab = self.tab_transactions
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        filters = tk.Frame(
            tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        filters.columnconfigure(4, weight=1)

        for column, title in enumerate(("Период", "Даты", "Тип", "Категория")):
            tk.Label(
                filters, text=title, bg=SURFACE, fg=MUTED, font=FONT_SMALL
            ).grid(row=0, column=column, sticky="w", padx=(10, 0), pady=(12, 0))

        self.period_combo = ttk.Combobox(
            filters,
            textvariable=self.period_var,
            values=[label for label, _code in PERIODS],
            state="readonly",
            width=15,
        )
        self.period_combo.grid(row=1, column=0, sticky="w", padx=(10, 0), pady=(4, 12))

        dates = tk.Frame(filters, bg=SURFACE)
        dates.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 12))
        self.date_from_entry = ttk.Entry(
            dates, textvariable=self.date_from_var, width=10, state="disabled"
        )
        self.date_from_entry.pack(side="left")
        tk.Label(dates, text="—", bg=SURFACE, fg=MUTED).pack(side="left", padx=3)
        self.date_to_entry = ttk.Entry(
            dates, textvariable=self.date_to_var, width=10, state="disabled"
        )
        self.date_to_entry.pack(side="left")

        self.kind_combo = ttk.Combobox(
            filters,
            textvariable=self.kind_var,
            values=[ALL_KINDS, *KIND_LABELS.values()],
            state="readonly",
            width=13,
        )
        self.kind_combo.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(4, 12))

        self.category_combo = ttk.Combobox(
            filters,
            textvariable=self.category_var,
            values=[ALL_CATEGORIES],
            state="readonly",
            width=16,
        )
        self.category_combo.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(4, 12))

        ttk.Button(filters, text="Сбросить", command=self.reset_filters).grid(
            row=1, column=4, sticky="e", padx=10, pady=(4, 12)
        )

        search_frame = tk.Frame(filters, bg=SURFACE)
        search_frame.grid(
            row=2, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 12)
        )
        tk.Label(
            search_frame, text="Поиск", bg=SURFACE, fg=MUTED, font=FONT_SMALL
        ).pack(side="left", padx=(0, 8))
        ttk.Entry(search_frame, textvariable=self.search_var, width=14).pack(
            side="left", fill="x", expand=True
        )

        table_card = tk.Frame(
            tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        table_card.grid(row=2, column=0, sticky="nsew")
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_card,
            columns=("date", "kind", "category", "amount", "comment"),
            show="headings",
            selectmode="browse",
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
        scroll = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=1)
        self.tree.configure(yscrollcommand=scroll.set)

        headings = (
            ("date", "Дата", 105, "w"),
            ("kind", "Тип", 95, "w"),
            ("category", "Категория", 190, "w"),
            ("amount", "Сумма", 150, "e"),
            ("comment", "Комментарий", 260, "w"),
        )
        for column, title, width, anchor in headings:
            self.tree.heading(column, text=title, anchor=anchor)
            self.tree.column(
                column, width=width, anchor=anchor, stretch=(column == "comment")
            )
        self.tree.tag_configure(KIND_INCOME, foreground=INCOME)
        self.tree.tag_configure(KIND_EXPENSE, foreground=EXPENSE)
        self.tree.bind("<Double-1>", self.edit_transaction)
        self.tree.bind("<Return>", self.edit_transaction)
        self.tree.bind("<Delete>", self.delete_transaction)

        self.empty_label = tk.Label(
            table_card,
            text=(
                "Операций пока нет.\n"
                "Нажмите «+ Добавить операцию», чтобы создать первую запись."
            ),
            bg=SURFACE,
            fg=MUTED,
            font=FONT_BASE,
            justify="center",
        )

        footer = tk.Frame(tab, bg=BG)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        tk.Label(
            footer, textvariable=self.footer_var, bg=BG, fg=MUTED, font=FONT_SMALL
        ).grid(row=0, column=0, sticky="w")
        actions = tk.Frame(footer, bg=BG)
        actions.grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="Изменить", command=self.edit_transaction).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            actions, text="Удалить", style="Danger.TButton", command=self.delete_transaction
        ).pack(side="left")

    def _build_categories_tab(self) -> None:
        tab = self.tab_categories
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        info = tk.Frame(
            tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        info.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(
            info,
            text=(
                "Категории по умолчанию описаны словарём в finance/categories.py "
                "и создаются при первом запуске. Названия уникальны; удалить можно "
                "только категорию без операций."
            ),
            bg=SURFACE,
            fg=MUTED,
            font=FONT_SMALL,
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=16, pady=12)

        table_card = tk.Frame(
            tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        table_card.grid(row=2, column=0, sticky="nsew")
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(0, weight=1)
        self.category_tree = ttk.Treeview(
            table_card,
            columns=("kind", "name", "count", "total"),
            show="headings",
            selectmode="browse",
        )
        self.category_tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
        scroll = ttk.Scrollbar(
            table_card, orient="vertical", command=self.category_tree.yview
        )
        scroll.grid(row=0, column=1, sticky="ns", pady=1)
        self.category_tree.configure(yscrollcommand=scroll.set)
        for column, title, width, anchor in (
            ("kind", "Тип", 110, "w"),
            ("name", "Категория", 260, "w"),
            ("count", "Операций", 110, "center"),
            ("total", "Сумма", 160, "e"),
        ):
            self.category_tree.heading(column, text=title, anchor=anchor)
            self.category_tree.column(
                column, width=width, anchor=anchor, stretch=(column == "name")
            )
        self.category_tree.tag_configure(KIND_INCOME, foreground=INCOME)
        self.category_tree.tag_configure(KIND_EXPENSE, foreground=EXPENSE)
        self.category_tree.bind("<Double-1>", self.rename_category)

        footer = tk.Frame(tab, bg=BG)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        tk.Label(
            footer,
            text="Двойной щелчок по строке — переименование.",
            bg=BG,
            fg=MUTED,
            font=FONT_SMALL,
        ).grid(row=0, column=0, sticky="w")
        actions = tk.Frame(footer, bg=BG)
        actions.grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="Добавить", command=self.add_category).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Переименовать", command=self.rename_category).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            actions, text="Удалить", style="Danger.TButton", command=self.delete_category
        ).pack(side="left")

    def _build_analytics_tab(self) -> None:
        tab = self.tab_analytics
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(1, weight=1)

        top = tk.Frame(tab, bg=BG)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        tk.Label(
            top, text="Аналитика", bg=BG, fg=TEXT, font=(FONT_FAMILY, 12, "bold")
        ).pack(side="left")
        tk.Label(
            top, textvariable=self.analytics_period_var, bg=BG, fg=MUTED, font=FONT_SMALL
        ).pack(side="left", padx=12)

        chart_card = tk.Frame(
            tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        chart_card.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        chart_card.columnconfigure(0, weight=1)
        chart_card.rowconfigure(1, weight=1)
        ttk.Label(
            chart_card, text="Расходы по категориям", style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.chart = tk.Canvas(
            chart_card, bg=SURFACE, highlightthickness=0, bd=0
        )
        self.chart.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.chart.bind("<Configure>", lambda _event: self._redraw_chart())

        income_card = tk.Frame(
            tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        income_card.grid(row=1, column=1, sticky="nsew")
        income_card.columnconfigure(0, weight=1)
        income_card.rowconfigure(2, weight=1)
        ttk.Label(
            income_card, text="Доходы по категориям", style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 0))
        ttk.Label(
            income_card, textvariable=self.income_total_var, style="CardHint.TLabel"
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(2, 6))
        self.income_list = tk.Frame(income_card, bg=SURFACE)
        self.income_list.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self, bg=SURFACE)
        bar.grid(row=3, column=0, sticky="ew")
        tk.Frame(bar, bg=BORDER, height=1).pack(fill="x")
        tk.Label(
            bar, textvariable=self.status_var, bg=SURFACE, fg=MUTED, font=FONT_SMALL
        ).pack(anchor="w", padx=22, pady=7)

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-n>", lambda _event: self.add_transaction(KIND_EXPENSE))
        self.bind("<F5>", lambda _event: self.reload_all())
        self.period_combo.bind("<<ComboboxSelected>>", self._on_period_changed)
        self.kind_combo.bind("<<ComboboxSelected>>", self._on_kind_changed)
        self.category_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_transactions())
        self.search_var.trace_add("write", self._on_search_changed)
        for entry in (self.date_from_entry, self.date_to_entry):
            entry.bind("<Return>", lambda _event: self.refresh_transactions())
            entry.bind("<FocusOut>", lambda _event: self.refresh_transactions())

    def _center(self) -> None:
        """Ставит окно по центру, уменьшая его под небольшой экран."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(WINDOW_SIZE[0], screen_width - 40)
        height = min(WINDOW_SIZE[1], screen_height - 110)
        self.minsize(
            min(MIN_WINDOW_SIZE[0], width),
            min(MIN_WINDOW_SIZE[1], height),
        )
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------
    # Обновление данных
    # ------------------------------------------------------------------
    def reload_all(self) -> None:
        """Перечитывает категории и операции из БД."""
        self._categories = self.service.categories()
        self.store.reload(self._categories)
        self._refresh_category_filter()
        self._refresh_categories_tree()
        self.refresh_transactions()

    def refresh_transactions(self) -> None:
        self._search_job = None
        flt = self._current_filter()
        rows = self.service.transactions(flt)
        self._rows = rows
        self._fill_tree(rows)
        self._update_footer(rows)

        period = self._period_only_filter()
        summary = self.service.summary(period)
        self._update_cards(summary, period)
        self._chart_rows = self.service.totals_by_category(period, KIND_EXPENSE)
        self._income_rows = self.service.totals_by_category(period, KIND_INCOME)
        self._update_analytics(period)
        self._update_status()

    def _refresh_category_filter(self) -> None:
        kind = self._selected_kind()
        self._category_options = {
            item.name: item.id for item in self.store.all(kind)
        }
        values = [ALL_CATEGORIES, *self._category_options]
        self.category_combo.configure(values=values)
        if (
            self.category_var.get() != ALL_CATEGORIES
            and self.category_var.get() not in self._category_options
        ):
            self.category_var.set(ALL_CATEGORIES)

    def _refresh_categories_tree(self) -> None:
        self.category_tree.delete(*self.category_tree.get_children())
        for item in self._categories:
            sign = "+" if item.kind == KIND_INCOME else "−"
            total = f"{sign} {format_money(item.total)}" if item.transactions else "—"
            self.category_tree.insert(
                "",
                "end",
                iid=str(item.id),
                values=(
                    KIND_LABELS.get(item.kind, item.kind),
                    item.name,
                    item.transactions,
                    total,
                ),
                tags=(item.kind,),
            )

    def _fill_tree(self, rows: list[TransactionRow]) -> None:
        self.tree.delete(*self.tree.get_children())
        if rows:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            self.empty_label.lift()
        for row in rows:
            sign = "+" if row.kind == KIND_INCOME else "−"
            self.tree.insert(
                "",
                "end",
                iid=str(row.id),
                values=(
                    format_date(row.occurred_on),
                    KIND_LABELS.get(row.kind, row.kind),
                    row.category_name,
                    f"{sign} {format_money(row.amount)}",
                    row.comment,
                ),
                tags=(row.kind,),
            )

    def _update_footer(self, rows: list[TransactionRow]) -> None:
        income = sum((r.amount for r in rows if r.kind == KIND_INCOME), ZERO)
        expense = sum((r.amount for r in rows if r.kind == KIND_EXPENSE), ZERO)
        self.footer_var.set(
            f"Показано операций: {len(rows)}   ·   "
            f"Доходы: {format_money(income)}   ·   "
            f"Расходы: {format_money(expense)}   ·   "
            f"Итог: {format_money(income - expense)}"
        )

    def _update_cards(self, summary: Summary, period: TransactionFilter) -> None:
        self.balance_var.set(format_money(summary.balance))
        self.income_var.set(format_money(summary.income))
        self.expense_var.set(format_money(summary.expense))
        self.balance_label.configure(
            foreground=INCOME if summary.balance >= 0 else EXPENSE
        )
        self.card_hint_var.set(f"Период: {format_period(period.date_from, period.date_to)}")

    def _update_analytics(self, period: TransactionFilter) -> None:
        self.analytics_period_var.set(
            f"Период: {format_period(period.date_from, period.date_to)}"
        )
        self._redraw_chart()
        self._render_income_list()

    def _update_status(self) -> None:
        self.status_var.set(
            f"База данных: {self.service.db.path.name}   ·   "
            f"Всего операций: {self.service.count_transactions()}   ·   "
            f"Категорий: {len(self._categories)}"
        )

    # ------------------------------------------------------------------
    # Аналитика и диаграмма
    # ------------------------------------------------------------------
    def _render_income_list(self) -> None:
        for child in self.income_list.winfo_children():
            child.destroy()
        total = sum((amount for _name, amount in self._income_rows), ZERO)
        self.income_total_var.set(f"Всего: {format_money(total)}")
        if not self._income_rows:
            tk.Label(
                self.income_list,
                text="Нет доходов за выбранный период",
                bg=SURFACE,
                fg=MUTED,
                font=FONT_SMALL,
            ).grid(row=0, column=0, sticky="w", pady=8)
            return
        self.income_list.columnconfigure(0, weight=1)
        for index, (name, amount) in enumerate(self._income_rows[:8]):
            tk.Label(
                self.income_list,
                text=name,
                bg=SURFACE,
                fg=TEXT,
                font=FONT_BASE,
                anchor="w",
            ).grid(row=index, column=0, sticky="w", pady=3)
            tk.Label(
                self.income_list,
                text=format_money(amount),
                bg=SURFACE,
                fg=INCOME,
                font=FONT_BASE,
                anchor="e",
            ).grid(row=index, column=1, sticky="e", pady=3)
        if len(self._income_rows) > 8:
            tk.Label(
                self.income_list,
                text=f"… и ещё {len(self._income_rows) - 8}",
                bg=SURFACE,
                fg=MUTED,
                font=FONT_SMALL,
            ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _redraw_chart(self) -> None:
        canvas = self.chart
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 50 or height < 50:
            return
        if not self._chart_rows:
            canvas.create_text(
                width / 2,
                height / 2,
                text="Нет расходов за выбранный период",
                fill=MUTED,
                font=FONT_SMALL,
            )
            return

        max_rows = max(1, (height - 24) // 30)
        rows = self._chart_rows[:max_rows]
        label_width = min(190, int(width * 0.32))
        value_width = 110
        bar_area = max(40, width - label_width - value_width - 24)
        max_amount = max(float(amount) for _name, amount in rows) or 1.0
        row_height = min(34, max(24, (height - 20) // len(rows)))

        for index, (name, amount) in enumerate(rows):
            y = 10 + index * row_height
            center = y + row_height / 2
            canvas.create_text(
                6, center, text=name, anchor="w", fill=TEXT, font=FONT_BASE
            )
            bar_width = max(4, int(bar_area * float(amount) / max_amount))
            color = CHART_COLORS[index % len(CHART_COLORS)]
            canvas.create_rectangle(
                label_width,
                center - 8,
                label_width + bar_width,
                center + 8,
                fill=color,
                outline="",
            )
            canvas.create_text(
                label_width + bar_width + 8,
                center,
                text=format_money(amount),
                anchor="w",
                fill=MUTED,
                font=FONT_SMALL,
            )
        if len(self._chart_rows) > len(rows):
            canvas.create_text(
                6,
                height - 8,
                text=f"Показаны {len(rows)} из {len(self._chart_rows)} категорий",
                anchor="sw",
                fill=MUTED,
                font=FONT_SMALL,
            )

    # ------------------------------------------------------------------
    # Фильтры
    # ------------------------------------------------------------------
    def _selected_kind(self) -> str | None:
        return self._kind_labels.get(self.kind_var.get())

    def _selected_category_id(self) -> int | None:
        if self.category_var.get() == ALL_CATEGORIES:
            return None
        return self._category_options.get(self.category_var.get())

    def _period_range(self) -> tuple[date | None, date | None]:
        code = PERIOD_CODES.get(self.period_var.get(), "month")
        today = date.today()
        if code == "month":
            return month_bounds(today)
        if code == "prev_month":
            return previous_month_bounds(today)
        if code == "year":
            return year_bounds(today)
        if code == "custom":
            start = self._parse_optional_date(self.date_from_var.get())
            end = self._parse_optional_date(self.date_to_var.get())
            return start, end
        return None, None

    @staticmethod
    def _parse_optional_date(text: str) -> date | None:
        text = text.strip()
        if not text:
            return None
        try:
            return parse_date(text)
        except ValueError:
            return None

    def _period_only_filter(self) -> TransactionFilter:
        start, end = self._period_range()
        return TransactionFilter(date_from=start, date_to=end)

    def _current_filter(self) -> TransactionFilter:
        start, end = self._period_range()
        return TransactionFilter(
            date_from=start,
            date_to=end,
            kind=self._selected_kind(),
            category_id=self._selected_category_id(),
            search=self.search_var.get(),
        )

    def _sync_date_entries(self) -> None:
        is_custom = PERIOD_CODES.get(self.period_var.get()) == "custom"
        if not is_custom:
            start, end = self._period_range()
            self.date_from_var.set(format_date(start) if start else "")
            self.date_to_var.set(format_date(end) if end else "")
        self.date_from_entry.configure(state="normal" if is_custom else "disabled")
        self.date_to_entry.configure(state="normal" if is_custom else "disabled")

    def _on_period_changed(self, _event=None) -> None:
        is_custom = PERIOD_CODES.get(self.period_var.get()) == "custom"
        dates_empty = (
            not self.date_from_var.get().strip()
            and not self.date_to_var.get().strip()
        )
        if is_custom and dates_empty:
            start, end = month_bounds(date.today())
            self.date_from_var.set(format_date(start))
            self.date_to_var.set(format_date(end))
        self._sync_date_entries()
        self.refresh_transactions()

    def _on_kind_changed(self, _event=None) -> None:
        self._refresh_category_filter()
        self.refresh_transactions()

    def _on_search_changed(self, *_args) -> None:
        if self._search_job is not None:
            self.after_cancel(self._search_job)
        self._search_job = self.after(250, self.refresh_transactions)

    def reset_filters(self) -> None:
        self.period_var.set(PERIODS[0][0])
        self.date_from_var.set("")
        self.date_to_var.set("")
        self._sync_date_entries()
        self.kind_var.set(ALL_KINDS)
        self._refresh_category_filter()
        self.category_var.set(ALL_CATEGORIES)
        self.search_var.set("")
        self.refresh_transactions()

    # ------------------------------------------------------------------
    # Действия с операциями
    # ------------------------------------------------------------------
    def add_transaction(self, kind: str = KIND_EXPENSE) -> None:
        dialog = TransactionDialog(
            self, self.service, self.store, default_kind=kind
        )
        self.wait_window(dialog)
        if dialog.saved:
            self.reload_all()
            if dialog.transaction_id is not None:
                self._select_transaction(dialog.transaction_id)

    def edit_transaction(self, _event=None) -> None:
        row = self._selected_transaction()
        if row is None:
            return
        dialog = TransactionDialog(
            self, self.service, self.store, transaction=row
        )
        self.wait_window(dialog)
        if dialog.saved:
            self.reload_all()
            self._select_transaction(row.id)

    def delete_transaction(self, _event=None) -> None:
        row = self._selected_transaction()
        if row is None:
            return
        question = (
            f"Удалить операцию «{row.category_name}» "
            f"на {format_money(row.amount)} от {format_date(row.occurred_on)}?"
        )
        if not messagebox.askyesno("Удаление операции", question, parent=self):
            return
        try:
            self.service.delete_transaction(row.id)
        except ValueError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.reload_all()

    def _selected_transaction(self) -> TransactionRow | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(
                "Операции", "Сначала выберите операцию в таблице.", parent=self
            )
            return None
        try:
            transaction_id = int(selection[0])
        except ValueError:
            return None
        return next((row for row in self._rows if row.id == transaction_id), None)

    def _select_transaction(self, transaction_id: int) -> None:
        item = str(transaction_id)
        if self.tree.exists(item):
            self.tree.selection_set(item)
            self.tree.focus(item)
            self.tree.see(item)

    # ------------------------------------------------------------------
    # Действия с категориями
    # ------------------------------------------------------------------
    def add_category(self) -> None:
        dialog = CategoryDialog(
            self,
            self.service,
            default_kind=self._selected_kind() or KIND_EXPENSE,
        )
        self.wait_window(dialog)
        if dialog.saved:
            self.reload_all()

    def rename_category(self, _event=None) -> None:
        category = self._selected_category()
        if category is None:
            return
        dialog = CategoryDialog(self, self.service, category=category)
        self.wait_window(dialog)
        if dialog.saved:
            self.reload_all()

    def delete_category(self) -> None:
        category = self._selected_category()
        if category is None:
            return
        question = (
            f"Удалить категорию «{category.name}»?\n"
            f"Операций в ней: {category.transactions}."
        )
        if not messagebox.askyesno("Удаление категории", question, parent=self):
            return
        try:
            self.service.delete_category(category.id)
        except ValueError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.reload_all()

    def _selected_category(self) -> CategoryInfo | None:
        selection = self.category_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Категории", "Сначала выберите категорию в таблице.", parent=self
            )
            return None
        try:
            category_id = int(selection[0])
        except ValueError:
            return None
        return next((item for item in self._categories if item.id == category_id), None)

    # ------------------------------------------------------------------
    def _show_about(self) -> None:
        messagebox.showinfo(
            "О программе",
            f"{APP_NAME}\nВерсия {APP_VERSION}\n\n"
            "Учёт доходов и расходов по категориям.\n"
            "Интерфейс — Tkinter, работа с данными — SQLAlchemy, "
            "хранилище — SQLite.",
            parent=self,
        )
