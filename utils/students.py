"""students.py — business logic for student/member records."""

import re
from datetime import date
from utils.json_utils import (
    read_json, find_record, add_record, update_record, delete_record, next_id
)

FILE = "students.json"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_all_students():
    return read_json(FILE)


def get_student(student_id):
    return find_record(FILE, student_id, "student_id")


def search_students(query="", course="", status=""):
    query = (query or "").strip().lower()
    course = (course or "").strip()
    status = (status or "").strip()
    results = []
    for s in get_all_students():
        if query and query not in s["student_id"].lower() \
                and query not in s["name"].lower() \
                and query not in s["email"].lower():
            continue
        if course and s["course"] != course:
            continue
        if status and s["membership_status"] != status:
            continue
        results.append(s)
    return results


def get_courses():
    return sorted({s["course"] for s in read_json(FILE) if s.get("course")})


def validate_student_data(data, is_new=True):
    errors = []
    required = ["name", "email", "phone", "course", "year", "department"]
    for field in required:
        if not str(data.get(field, "")).strip():
            errors.append(f"'{field.replace('_', ' ').title()}' is required.")

    email = str(data.get("email", "")).strip()
    if email and not EMAIL_RE.match(email):
        errors.append("Email address is not valid.")

    phone = str(data.get("phone", "")).strip()
    if phone and not re.match(r"^\+?\d{7,15}$", phone):
        errors.append("Phone number should be 7-15 digits.")

    try:
        year = int(data.get("year", 0))
        if year < 1 or year > 8:
            errors.append("Year should be between 1 and 8.")
    except (ValueError, TypeError):
        errors.append("Year must be a number.")

    if is_new and email:
        students = read_json(FILE)
        if any(s["email"].lower() == email.lower() for s in students):
            errors.append(f"Email '{email}' is already registered.")

    return errors


def create_student(data):
    errors = validate_student_data(data, is_new=True)
    if errors:
        return None, errors

    student_id = next_id(FILE, "student_id", "S")
    record = {
        "student_id": student_id,
        "name": str(data.get("name", "")).strip(),
        "email": str(data.get("email", "")).strip(),
        "phone": str(data.get("phone", "")).strip(),
        "course": str(data.get("course", "")).strip(),
        "year": int(data.get("year")),
        "department": str(data.get("department", "")).strip(),
        "registration_date": str(data.get("registration_date") or date.today().isoformat()),
        "membership_status": data.get("membership_status", "Active") or "Active",
    }
    add_record(FILE, record, "student_id")
    return record, []


def update_student(student_id, data):
    if not find_record(FILE, student_id, "student_id"):
        return None, ["Student not found."]
    errors = validate_student_data(data, is_new=False)
    if errors:
        return None, errors
    updates = {
        "name": str(data.get("name", "")).strip(),
        "email": str(data.get("email", "")).strip(),
        "phone": str(data.get("phone", "")).strip(),
        "course": str(data.get("course", "")).strip(),
        "year": int(data.get("year")),
        "department": str(data.get("department", "")).strip(),
        "membership_status": data.get("membership_status", "Active"),
    }
    record = update_record(FILE, student_id, "student_id", updates)
    return record, []


def delete_student(student_id):
    from utils.transactions import has_active_transactions_for_student
    if has_active_transactions_for_student(student_id):
        return False, "This student has books currently on loan and cannot be deleted."
    try:
        delete_record(FILE, student_id, "student_id")
        return True, None
    except ValueError as e:
        return False, str(e)
