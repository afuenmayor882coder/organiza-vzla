"""
Formatting helpers for dates, currency, and display values.
"""

from datetime import datetime


def format_date(dt: datetime | None, include_time: bool = False) -> str:
    if dt is None:
        return "—"
    if include_time:
        return dt.strftime("%d/%m/%Y %H:%M")
    return dt.strftime("%d/%m/%Y")


def format_currency(amount: float, currency: str = "USD") -> str:
    if currency == "VES":
        return f"Bs. {amount:,.2f}"
    return f"$ {amount:,.2f}"


def format_quantity(qty: int, packaging: str = "") -> str:
    if packaging:
        return f"{qty:,} {packaging}"
    return f"{qty:,}"


def truncate_text(text: str, max_length: int = 50) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
