"""
transactions.py — issuing, returning, overdue/fine calculation and
transaction-history lookups. This is the heart of the LMS: it's the only
module allowed to touch both books.json and students.json state together.
"""

from datetime import date, datetime, timedelta

from utils.json_utils import read_json, find_record, add_record, update_record, next_id
from utils.books import get_book, change_available_copies
from utils.students import get_student

FILE = "transactions.json"


def _settings():
    return read_json("settings.json") or {
        "borrowing_period_days": 14, "fine_per_day": 5, "currency_symbol": "\u20b9"
    }


def _parse(d):
    return datetime.strptime(d, "%Y-%m-%d").date()


def overdue_days(due_date_str, return_date_str=None, today=None):
    today = today or date.today()
    due = _parse(due_date_str)
    end = _parse(return_date_str) if return_date_str else today
    delta = (end - due).days
    return max(delta, 0)


def calculate_fine(due_date_str, return_date_str=None, today=None):
    settings = _settings()
    days = overdue_days(due_date_str, return_date_str, today)
    return days * settings.get("fine_per_day", 5)


def _enrich(txn, today=None):
    """Add computed fields: book/student snapshot, live status, live fine."""
    txn = dict(txn)
    book = get_book(txn["book_id"])
    student = get_student(txn["student_id"])
    txn["book_title"] = book["title"] if book else "(deleted book)"
    txn["book"] = book
    txn["student_name"] = student["name"] if student else "(deleted student)"
    txn["student"] = student

    if txn["status"] == "Returned":
        txn["display_status"] = "Returned"
        txn["live_fine"] = txn.get("fine", 0)
    else:
        days = overdue_days(txn["due_date"], None, today)
        txn["overdue_days"] = days
        txn["display_status"] = "Overdue" if days > 0 else "Active"
        txn["live_fine"] = calculate_fine(txn["due_date"], None, today) if days > 0 else 0
    return txn


def get_all_transactions():
    return [_enrich(t) for t in read_json(FILE)]


def get_transaction(transaction_id):
    t = find_record(FILE, transaction_id, "transaction_id")
    return _enrich(t) if t else None


def filter_transactions(status=None, student_id=None, book_id=None, query=None):
    status = (status or "").strip()
    query = (query or "").strip().lower()
    results = []
    for t in get_all_transactions():
        if status and t["display_status"] != status:
            continue
        if student_id and t["student_id"] != student_id:
            continue
        if book_id and t["book_id"] != book_id:
            continue
        if query and query not in t["transaction_id"].lower() \
                and query not in t["student_id"].lower() \
                and query not in t["book_id"].lower() \
                and query not in (t["student_name"] or "").lower() \
                and query not in (t["book_title"] or "").lower():
            continue
        results.append(t)
    results.sort(key=lambda t: t["issue_date"], reverse=True)
    return results


def has_active_transactions_for_book(book_id):
    return any(t["book_id"] == book_id and t["status"] == "Active" for t in read_json(FILE))


def has_active_transactions_for_student(student_id):
    return any(t["student_id"] == student_id and t["status"] == "Active" for t in read_json(FILE))


def active_transactions_for_student(student_id):
    return [t for t in get_all_transactions()
            if t["student_id"] == student_id and t["status"] == "Active"]


def history_for_student(student_id):
    txns = [t for t in get_all_transactions() if t["student_id"] == student_id]
    txns.sort(key=lambda t: t["issue_date"], reverse=True)
    return txns


def history_for_book(book_id):
    txns = [t for t in get_all_transactions() if t["book_id"] == book_id]
    txns.sort(key=lambda t: t["issue_date"], reverse=True)
    return txns


def issue_book(student_id, book_id):
    """Issue `book_id` to `student_id`. Returns (transaction, error_message)."""
    student = get_student(student_id)
    if not student:
        return None, "Student not found."
    if student.get("membership_status") != "Active":
        return None, f"'{student['name']}' has a {student['membership_status'].lower()} membership and cannot borrow books."

    book = get_book(book_id)
    if not book:
        return None, "Book not found."
    if book["available_copies"] <= 0:
        return None, f"'{book['title']}' has no available copies right now."

    settings = _settings()
    max_loans = settings.get("max_active_loans_per_student", 5)
    if len(active_transactions_for_student(student_id)) >= max_loans:
        return None, f"'{student['name']}' already has the maximum of {max_loans} books issued."

    already = [t for t in read_json(FILE)
               if t["student_id"] == student_id and t["book_id"] == book_id and t["status"] == "Active"]
    if already:
        return None, f"'{student['name']}' already has an active loan for this book."

    issue_date = date.today()
    due_date = issue_date + timedelta(days=settings.get("borrowing_period_days", 14))

    transaction_id = next_id(FILE, "transaction_id", "T")
    record = {
        "transaction_id": transaction_id,
        "student_id": student_id,
        "book_id": book_id,
        "issue_date": issue_date.isoformat(),
        "due_date": due_date.isoformat(),
        "return_date": None,
        "status": "Active",
        "fine": 0,
        "fine_paid": False,
    }
    add_record(FILE, record, "transaction_id")
    change_available_copies(book_id, -1)
    return record, None


def return_book(transaction_id):
    """Mark a transaction returned, compute the final fine, restock the book.
    Returns (transaction, error_message)."""
    txn = find_record(FILE, transaction_id, "transaction_id")
    if not txn:
        return None, "Transaction not found."
    if txn["status"] == "Returned":
        return None, "This book has already been returned."

    return_date = date.today()
    fine = calculate_fine(txn["due_date"], return_date.isoformat())

    updates = {
        "return_date": return_date.isoformat(),
        "status": "Returned",
        "fine": fine,
        "fine_paid": fine == 0,
    }
    record = update_record(FILE, transaction_id, "transaction_id", updates)
    change_available_copies(txn["book_id"], +1)
    return record, None


def mark_fine_paid(transaction_id):
    txn = find_record(FILE, transaction_id, "transaction_id")
    if not txn:
        return None, "Transaction not found."
    if txn.get("fine", 0) <= 0:
        return None, "This transaction has no fine to pay."
    record = update_record(FILE, transaction_id, "transaction_id", {"fine_paid": True})
    return record, None
