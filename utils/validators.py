"""
Data validation functions. Called before writing to MongoDB to catch
bad input early and return user-friendly Spanish error messages.
"""


def validate_positive_quantity(quantity: int) -> str | None:
    """Returns an error message or None if valid."""
    if quantity is None:
        return "La cantidad es obligatoria."
    if quantity <= 0:
        return "La cantidad debe ser mayor a cero."
    return None


def validate_required_text(value: str, field_label: str) -> str | None:
    if not value or not value.strip():
        return f'El campo "{field_label}" es obligatorio.'
    return None


def validate_stock_availability(requested: int, available: int) -> str | None:
    if requested > available:
        return f"Stock insuficiente. Disponible: {available}."
    return None


def validate_positive_amount(amount: float) -> str | None:
    if amount is None:
        return "El monto es obligatorio."
    if amount <= 0:
        return "El monto debe ser mayor a cero."
    return None


def validate_email(email: str) -> str | None:
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return "Ingrese un correo electronico valido."
    return None


def validate_donation_form(
    category: str,
    item_id: str,
    quantity: int,
    donor_name: str,
) -> list[str]:
    """Validate all required donation fields. Returns list of error messages (empty = valid)."""
    errors = []
    err = validate_required_text(category, "Categoria")
    if err:
        errors.append(err)
    err = validate_required_text(item_id, "Articulo")
    if err:
        errors.append(err)
    err = validate_positive_quantity(quantity)
    if err:
        errors.append(err)
    err = validate_required_text(donor_name, "Donante")
    if err:
        errors.append(err)
    return errors


def validate_exit_form(
    item_id: str,
    quantity: int,
    available_stock: int,
    recipient_name: str,
) -> list[str]:
    """Validate all required exit fields. Returns list of error messages (empty = valid)."""
    errors = []
    err = validate_required_text(item_id, "Articulo")
    if err:
        errors.append(err)
    err = validate_positive_quantity(quantity)
    if err:
        errors.append(err)
    if not errors:
        err = validate_stock_availability(quantity, available_stock)
        if err:
            errors.append(err)
    err = validate_required_text(recipient_name, "Nombre del Receptor")
    if err:
        errors.append(err)
    return errors


def validate_transaction_form(
    amount: float,
    description: str,
    niif_category: str,
    subcategory: str,
) -> list[str]:
    """Validate all required cash flow fields. Returns list of error messages (empty = valid)."""
    errors = []
    err = validate_positive_amount(amount)
    if err:
        errors.append(err)
    err = validate_required_text(description, "Descripcion")
    if err:
        errors.append(err)
    err = validate_required_text(niif_category, "Categoria NIIF")
    if err:
        errors.append(err)
    err = validate_required_text(subcategory, "Subcategoria")
    if err:
        errors.append(err)
    return errors
