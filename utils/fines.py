"""fines.py — fine aggregation views built on top of transactions.py."""

from utils.transactions import get_all_transactions, calculate_fine
from utils.json_utils import read_json


def pending_fines():
    """Fines that are owed right now: unpaid returned-late fines PLUS the
    live (still-accruing) fine on any active overdue loan."""
    rows = []
    for t in get_all_transactions():
        if t["status"] == "Returned" and t.get("fine", 0) > 0 and not t.get("fine_paid"):
            rows.append(t)
        elif t["display_status"] == "Overdue" and t["live_fine"] > 0:
            rows.append(t)
    return rows


def paid_fines():
    return [t for t in get_all_transactions()
            if t["status"] == "Returned" and t.get("fine", 0) > 0 and t.get("fine_paid")]


def total_pending_amount():
    total = 0
    for t in pending_fines():
        total += t.get("fine") if t["status"] == "Returned" else t["live_fine"]
    return total


def fines_by_student():
    """Group pending fine amounts by student for a student-wise breakdown."""
    grouped = {}
    for t in pending_fines():
        amount = t.get("fine") if t["status"] == "Returned" else t["live_fine"]
        key = t["student_id"]
        if key not in grouped:
            grouped[key] = {"student_id": key, "student_name": t["student_name"], "amount": 0, "count": 0}
        grouped[key]["amount"] += amount
        grouped[key]["count"] += 1
    return sorted(grouped.values(), key=lambda g: g["amount"], reverse=True)


def dashboard_stats():
    from utils.books import get_all_books
    from utils.students import get_all_students

    books = get_all_books()
    students = get_all_students()
    txns = get_all_transactions()

    total_book_copies = sum(b["total_copies"] for b in books)
    available_copies = sum(b["available_copies"] for b in books)
    issued_copies = total_book_copies - available_copies

    active = [t for t in txns if t["status"] == "Active"]
    overdue = [t for t in active if t["display_status"] == "Overdue"]

    recent_issued = sorted(txns, key=lambda t: t["issue_date"], reverse=True)[:5]
    recent_returned = sorted(
        [t for t in txns if t["status"] == "Returned"],
        key=lambda t: t["return_date"] or "", reverse=True
    )[:5]

    return {
        "total_books": total_book_copies,
        "total_titles": len(books),
        "available_books": available_copies,
        "issued_books": issued_copies,
        "total_students": len(students),
        "overdue_books": len(overdue),
        "pending_fines_total": total_pending_amount(),
        "recent_issued": recent_issued,
        "recent_returned": recent_returned,
        "active_loans": len(active),
    }
