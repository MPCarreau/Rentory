"""Use-case layer: atomic check-and-insert under an item row lock."""
from app import domain, repository


class ItemNotFound(Exception):
    pass


class ItemUnavailable(Exception):
    pass


def reserve(conn, user_id, item_id, start_date, end_date):
    domain.validate_dates(start_date, end_date)
    # The transaction begins with the connection context in the HTTP layer.
    # Lock BEFORE checking; competing requests for this item wait here.
    if repository.lock_item(conn, item_id) is None:
        raise ItemNotFound()
    if repository.conflicting_reservation(conn, item_id, start_date, end_date):
        raise ItemUnavailable()
    return repository.create_reservation(conn, user_id, item_id, start_date, end_date)
