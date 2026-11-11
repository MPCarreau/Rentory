from datetime import date


def validate_dates(start_date: date, end_date: date):
    """Pure business rule; no SQL, HTTP, or JWT dependencies."""
    if end_date <= start_date:
        raise ValueError("end_date must be after start_date")


def overlaps(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    """Half-open intervals: adjacent rentals do not overlap."""
    return start_a < end_b and start_b < end_a
