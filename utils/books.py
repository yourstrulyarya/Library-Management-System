"""
books.py — business logic for the book catalogue.
Every function returns plain dicts/lists ready to hand to a Jinja template.
"""

from utils.json_utils import (
    read_json, write_json, find_record, add_record,
    update_record, delete_record, next_id
)

FILE = "books.json"


def _with_status(book):
    """Attach a computed 'status' field so it can never go stale, no matter
    how available_copies changed since the book was last saved."""
    book = dict(book)
    if book.get("available_copies", 0) <= 0:
        book["status"] = "Unavailable"
    elif book.get("available_copies", 0) < book.get("total_copies", 0):
        book["status"] = "Partially Available"
    else:
        book["status"] = "Available"
    return book


def get_all_books():
    return [_with_status(b) for b in read_json(FILE)]


def get_book(book_id):
    book = find_record(FILE, book_id, "book_id")
    return _with_status(book) if book else None


def search_books(query="", category="", status="", course=None):
    query = (query or "").strip().lower()
    category = (category or "").strip()
    status = (status or "").strip()
    results = []
    for book in get_all_books():
        if query and query not in book["book_id"].lower() \
                and query not in book["isbn"].lower() \
                and query not in book["title"].lower() \
                and query not in book["author"].lower():
            continue
        if category and book["category"] != category:
            continue
        if status and book["status"] != status:
            continue
        results.append(book)
    return results


def get_categories():
    return sorted({b["category"] for b in read_json(FILE) if b.get("category")})


def validate_book_data(data, is_new=True, existing_id=None):
    """Returns a list of human-readable validation error strings (empty = ok)."""
    errors = []
    required = ["isbn", "title", "author", "category", "publisher",
                "publication_year", "total_copies", "shelf_number"]
    for field in required:
        if not str(data.get(field, "")).strip():
            errors.append(f"'{field.replace('_', ' ').title()}' is required.")

    try:
        total_copies = int(data.get("total_copies", 0))
        if total_copies < 0:
            errors.append("Total copies cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Total copies must be a whole number.")
        total_copies = None

    try:
        year = int(data.get("publication_year", 0))
        if year < 1450 or year > 2100:
            errors.append("Publication year looks invalid.")
    except (ValueError, TypeError):
        errors.append("Publication year must be a number.")

    if is_new:
        books = read_json(FILE)
        isbn = str(data.get("isbn", "")).strip()
        if isbn and any(b["isbn"] == isbn for b in books):
            errors.append(f"ISBN '{isbn}' is already used by another book.")

    return errors, total_copies


def create_book(data):
    errors, total_copies = validate_book_data(data, is_new=True)
    if errors:
        return None, errors

    book_id = next_id(FILE, "book_id", "B")
    record = {
        "book_id": book_id,
        "isbn": str(data.get("isbn", "")).strip(),
        "title": str(data.get("title", "")).strip(),
        "author": str(data.get("author", "")).strip(),
        "category": str(data.get("category", "")).strip(),
        "publisher": str(data.get("publisher", "")).strip(),
        "publication_year": int(data.get("publication_year")),
        "total_copies": total_copies,
        "available_copies": total_copies,  # a brand new book starts fully available
        "shelf_number": str(data.get("shelf_number", "")).strip(),
    }
    add_record(FILE, record, "book_id")
    return record, []


def update_book(book_id, data):
    existing = find_record(FILE, book_id, "book_id")
    if not existing:
        return None, ["Book not found."]

    errors, total_copies = validate_book_data(data, is_new=False)
    if errors:
        return None, errors

    # available_copies can't exceed the (possibly changed) total, and can't
    # drop below the number currently on loan.
    on_loan = existing["total_copies"] - existing["available_copies"]
    if total_copies < on_loan:
        return None, [
            f"Total copies cannot be less than the {on_loan} copy(ies) currently issued."
        ]
    new_available = total_copies - on_loan

    updates = {
        "isbn": str(data.get("isbn", "")).strip(),
        "title": str(data.get("title", "")).strip(),
        "author": str(data.get("author", "")).strip(),
        "category": str(data.get("category", "")).strip(),
        "publisher": str(data.get("publisher", "")).strip(),
        "publication_year": int(data.get("publication_year")),
        "total_copies": total_copies,
        "available_copies": new_available,
        "shelf_number": str(data.get("shelf_number", "")).strip(),
    }
    record = update_record(FILE, book_id, "book_id", updates)
    return record, []


def delete_book(book_id):
    from utils.transactions import has_active_transactions_for_book
    if has_active_transactions_for_book(book_id):
        return False, "This book has copies currently on loan and cannot be deleted."
    try:
        delete_record(FILE, book_id, "book_id")
        return True, None
    except ValueError as e:
        return False, str(e)


def change_available_copies(book_id, delta):
    """Increase/decrease available_copies by delta (used on issue/return)."""
    book = find_record(FILE, book_id, "book_id")
    if not book:
        raise ValueError("Book not found.")
    new_value = book["available_copies"] + delta
    if new_value < 0 or new_value > book["total_copies"]:
        raise ValueError("Available copies would go out of range.")
    update_record(FILE, book_id, "book_id", {"available_copies": new_value})
