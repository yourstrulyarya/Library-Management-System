"""
app.py — Library Management System
Flask + Jinja2 + local JSON files. No database.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

from functools import wraps
from datetime import date

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, abort
)

from utils.json_utils import JSONStorageError, read_json, write_json
from utils import books as books_utils
from utils import students as students_utils
from utils import transactions as txn_utils
from utils import fines as fines_utils
from utils import auth as auth_utils

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"  # fine for a local college project


# ---------------------------------------------------------------------------
# Access-control helpers
# ---------------------------------------------------------------------------
def require_librarian(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "librarian":
            flash("Please sign in to access that page.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    settings = read_json("settings.json") or {}
    return {
        "library_name": settings.get("library_name", "Library Management System"),
        "currency": settings.get("currency_symbol", "\u20b9"),
        "current_role": session.get("role"),
        "display_name": session.get("display_name"),
        "today": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# Error handling — the app should never hard-crash on bad JSON / bad input
# ---------------------------------------------------------------------------
@app.errorhandler(JSONStorageError)
def handle_storage_error(e):
    return render_template("error.html", message=str(e)), 500


@app.errorhandler(404)
def handle_404(e):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if session.get("role") == "librarian":
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("role") == "librarian":
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        user, error = auth_utils.verify_login(user_id, password)
        if error:
            flash(error, "error")
            return render_template("login.html", user_id=user_id)
        session.clear()
        session["role"] = "librarian"
        session["user_id"] = user["user_id"]
        session["display_name"] = user.get("name", user["user_id"])
        flash(f"Welcome back, {session['display_name']}.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@require_librarian
def dashboard():
    stats = fines_utils.dashboard_stats()
    return render_template("dashboard.html", stats=stats)


# ---------------------------------------------------------------------------
# Book management
# ---------------------------------------------------------------------------
@app.route("/books")
@require_librarian
def list_books():
    query = request.args.get("q", "")
    category = request.args.get("category", "")
    status = request.args.get("status", "")
    results = books_utils.search_books(query, category, status)
    return render_template(
        "books.html", books=results, query=query, category=category, status=status,
        categories=books_utils.get_categories()
    )


@app.route("/books/<book_id>")
@require_librarian
def book_detail(book_id):
    book = books_utils.get_book(book_id)
    if not book:
        abort(404)
    history = txn_utils.history_for_book(book_id)
    return render_template("book_detail.html", book=book, history=history)


@app.route("/books/add", methods=["GET", "POST"])
@require_librarian
def add_book():
    if request.method == "POST":
        record, errors = books_utils.create_book(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("book_form.html", mode="add", book=request.form, categories=books_utils.get_categories())
        flash(f"'{record['title']}' was added to the catalogue as {record['book_id']}.", "success")
        return redirect(url_for("list_books"))
    return render_template("book_form.html", mode="add", book={}, categories=books_utils.get_categories())


@app.route("/books/edit/<book_id>", methods=["GET", "POST"])
@require_librarian
def edit_book(book_id):
    book = books_utils.get_book(book_id)
    if not book:
        abort(404)
    if request.method == "POST":
        record, errors = books_utils.update_book(book_id, request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            merged = dict(book)
            merged.update(request.form)
            return render_template("book_form.html", mode="edit", book=merged, categories=books_utils.get_categories())
        flash(f"'{record['title']}' was updated.", "success")
        return redirect(url_for("book_detail", book_id=book_id))
    return render_template("book_form.html", mode="edit", book=book, categories=books_utils.get_categories())


@app.route("/books/delete/<book_id>", methods=["POST"])
@require_librarian
def delete_book(book_id):
    ok, error = books_utils.delete_book(book_id)
    if ok:
        flash("Book removed from the catalogue.", "success")
    else:
        flash(error, "error")
    return redirect(url_for("list_books"))


# ---------------------------------------------------------------------------
# Student / member management
# ---------------------------------------------------------------------------
@app.route("/students")
@require_librarian
def list_students():
    query = request.args.get("q", "")
    course = request.args.get("course", "")
    status = request.args.get("status", "")
    results = students_utils.search_students(query, course, status)
    return render_template(
        "students.html", students=results, query=query, course=course, status=status,
        courses=students_utils.get_courses()
    )


@app.route("/students/<student_id>")
@require_librarian
def student_detail(student_id):
    student = students_utils.get_student(student_id)
    if not student:
        abort(404)
    active_loans = txn_utils.active_transactions_for_student(student_id)
    history = txn_utils.history_for_student(student_id)
    return render_template("student_detail.html", student=student, active_loans=active_loans, history=history)


@app.route("/students/add", methods=["GET", "POST"])
@require_librarian
def add_student():
    if request.method == "POST":
        record, errors = students_utils.create_student(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("student_form.html", mode="add", student=request.form)
        flash(f"'{record['name']}' was registered as {record['student_id']}.", "success")
        return redirect(url_for("list_students"))
    return render_template("student_form.html", mode="add", student={})


@app.route("/students/edit/<student_id>", methods=["GET", "POST"])
@require_librarian
def edit_student(student_id):
    student = students_utils.get_student(student_id)
    if not student:
        abort(404)
    if request.method == "POST":
        record, errors = students_utils.update_student(student_id, request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            merged = dict(student)
            merged.update(request.form)
            return render_template("student_form.html", mode="edit", student=merged)
        flash(f"'{record['name']}' was updated.", "success")
        return redirect(url_for("student_detail", student_id=student_id))
    return render_template("student_form.html", mode="edit", student=student)


@app.route("/students/delete/<student_id>", methods=["POST"])
@require_librarian
def delete_student(student_id):
    ok, error = students_utils.delete_student(student_id)
    if ok:
        flash("Member record deleted.", "success")
    else:
        flash(error, "error")
    return redirect(url_for("list_students"))


# ---------------------------------------------------------------------------
# Issue / Return
# ---------------------------------------------------------------------------
@app.route("/issue", methods=["GET", "POST"])
@require_librarian
def issue_book():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        book_id = request.form.get("book_id", "").strip()
        record, error = txn_utils.issue_book(student_id, book_id)
        if error:
            flash(error, "error")
        else:
            flash(f"Issued '{record['book_id']}' to '{record['student_id']}'. Due back {record['due_date']}.", "success")
        return redirect(url_for("issue_book"))
    return render_template(
        "issue_book.html",
        students=students_utils.get_all_students(),
        books=[b for b in books_utils.get_all_books() if b["available_copies"] > 0],
    )


@app.route("/return", methods=["GET", "POST"])
@require_librarian
def return_book():
    if request.method == "POST":
        transaction_id = request.form.get("transaction_id", "").strip()
        record, error = txn_utils.return_book(transaction_id)
        if error:
            flash(error, "error")
        else:
            fine_msg = f" A fine of {read_json('settings.json').get('currency_symbol','₹')}{record['fine']} applies." if record["fine"] > 0 else " Returned on time, no fine."
            flash(f"Transaction {record['transaction_id']} marked returned.{fine_msg}", "success")
        return redirect(url_for("return_book"))
    active = [t for t in txn_utils.get_all_transactions() if t["status"] == "Active"]
    active.sort(key=lambda t: t["due_date"])
    return render_template("return_book.html", active_loans=active)


# ---------------------------------------------------------------------------
# Transactions & Fines
# ---------------------------------------------------------------------------
@app.route("/transactions")
@require_librarian
def list_transactions():
    status = request.args.get("status", "")
    query = request.args.get("q", "")
    results = txn_utils.filter_transactions(status=status, query=query)
    return render_template("transactions.html", transactions=results, status=status, query=query)


@app.route("/fines")
@require_librarian
def fines_page():
    return render_template(
        "fines.html",
        pending=fines_utils.pending_fines(),
        paid=fines_utils.paid_fines(),
        by_student=fines_utils.fines_by_student(),
        total_pending=fines_utils.total_pending_amount(),
    )


@app.route("/fines/pay/<transaction_id>", methods=["POST"])
@require_librarian
def pay_fine(transaction_id):
    record, error = txn_utils.mark_fine_paid(transaction_id)
    if error:
        flash(error, "error")
    else:
        flash(f"Fine for transaction {transaction_id} marked as paid.", "success")
    return redirect(url_for("fines_page"))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@app.route("/settings", methods=["GET", "POST"])
@require_librarian
def settings_page():
    if request.method == "POST":
        try:
            data = {
                "library_name": request.form.get("library_name", "").strip() or "Library Management System",
                "borrowing_period_days": max(1, int(request.form.get("borrowing_period_days", 14))),
                "fine_per_day": max(0, int(request.form.get("fine_per_day", 5))),
                "currency_symbol": request.form.get("currency_symbol", "\u20b9").strip() or "\u20b9",
                "max_active_loans_per_student": max(1, int(request.form.get("max_active_loans_per_student", 5))),
            }
        except (ValueError, TypeError):
            flash("Settings must be valid numbers.", "error")
            return redirect(url_for("settings_page"))
        write_json("settings.json", data)
        flash("Settings updated.", "success")
        return redirect(url_for("settings_page"))
    return render_template("settings.html", settings=read_json("settings.json"))


if __name__ == "__main__":
    app.run(debug=True)
