"""
json_utils.py
--------------
Generic helpers for reading and writing the local JSON "database" files.
Every other module in utils/ builds on top of these four functions:
    read_json(filename)
    write_json(filename, data)
    add_record(filename, record, id_field)
    update_record(filename, record_id, id_field, updates)
    delete_record(filename, record_id, id_field)
    find_record(filename, record_id, id_field)
    search_records(filename, predicate)

Keeping all file I/O in one place means every route/business-logic function
gets consistent error handling and the JSON files never end up half-written.
"""

import json
import os
import threading

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# A simple in-process lock. Good enough for a single Flask dev-server process
# (this is a college project, not a production multi-worker deployment).
_lock = threading.Lock()


class JSONStorageError(Exception):
    """Raised when a JSON data file cannot be read or written safely."""
    pass


def _path(filename):
    return os.path.join(DATA_DIR, filename)


def read_json(filename):
    """Read a JSON file from the data/ directory. Returns [] if the file is
    missing (so the app can still boot) and raises JSONStorageError if the
    file exists but contains invalid JSON."""
    path = _path(filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError as e:
        raise JSONStorageError(f"'{filename}' contains invalid JSON: {e}")
    except OSError as e:
        raise JSONStorageError(f"Could not read '{filename}': {e}")


def write_json(filename, data):
    """Write data back to a JSON file atomically (write to a temp file, then
    replace) so a crash mid-write can never corrupt the real file."""
    path = _path(filename)
    tmp_path = path + ".tmp"
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with _lock:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
    except OSError as e:
        raise JSONStorageError(f"Could not write '{filename}': {e}")


def find_record(filename, record_id, id_field):
    """Return the first record whose id_field matches record_id, or None."""
    for record in read_json(filename):
        if record.get(id_field) == record_id:
            return record
    return None


def search_records(filename, predicate):
    """Return every record for which predicate(record) is True."""
    return [r for r in read_json(filename) if predicate(r)]


def add_record(filename, record, id_field):
    """Append a new record. Raises ValueError if the id already exists."""
    records = read_json(filename)
    if any(r.get(id_field) == record.get(id_field) for r in records):
        raise ValueError(f"A record with {id_field} '{record.get(id_field)}' already exists.")
    records.append(record)
    write_json(filename, records)
    return record


def update_record(filename, record_id, id_field, updates):
    """Merge `updates` into the record identified by record_id. Raises
    ValueError if no such record exists."""
    records = read_json(filename)
    for record in records:
        if record.get(id_field) == record_id:
            record.update(updates)
            write_json(filename, records)
            return record
    raise ValueError(f"No record found with {id_field} '{record_id}'.")


def delete_record(filename, record_id, id_field):
    """Remove the record identified by record_id. Raises ValueError if it
    does not exist."""
    records = read_json(filename)
    remaining = [r for r in records if r.get(id_field) != record_id]
    if len(remaining) == len(records):
        raise ValueError(f"No record found with {id_field} '{record_id}'.")
    write_json(filename, remaining)


def next_id(filename, id_field, prefix):
    """Generate the next sequential ID like 'B013' or 'S007' by looking at
    the highest existing numeric suffix for the given prefix."""
    records = read_json(filename)
    max_num = 0
    for r in records:
        val = str(r.get(id_field, ""))
        if val.startswith(prefix):
            suffix = val[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"
