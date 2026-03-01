"""Validation tools for order numbers and email addresses."""

import re


def validate_order_number(order_number: str) -> dict:
    """Validate that the order number is 6-12 alphanumeric characters.

    Args:
        order_number: The order number provided by the customer.

    Returns:
        A dict with keys 'valid' (bool) and 'message' (str).
    """
    cleaned = order_number.strip().upper()
    if re.match(r"^[A-Z0-9]{6,12}$", cleaned):
        return {"valid": True, "message": f"Order number {cleaned!r} is valid."}
    return {
        "valid": False,
        "message": (
            f"Order number {order_number!r} is invalid. "
            "It must be 6–12 alphanumeric characters (letters and digits only, no spaces or special chars)."
        ),
    }


def validate_email(email: str) -> dict:
    """Validate that the provided string is a well-formed email address.

    Args:
        email: The email address provided by the customer.

    Returns:
        A dict with keys 'valid' (bool) and 'message' (str).
    """
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email.strip()):
        return {"valid": True, "message": f"Email {email!r} is valid."}
    return {
        "valid": False,
        "message": (
            f"Email {email!r} does not look valid. "
            "Please ask the customer to confirm their email address."
        ),
    }
