def apply_discount(price: float, discount_percent: float) -> float:
    """Applies a percentage discount to a product price."""
    if price < 0:
        raise ValueError("Price cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount percent must be between 0 and 100")
    return round(price * (1 - discount_percent / 100), 2)
