# The Ivywood Athenaeum — Library Management System

A fully functional Library Management System built for a college project.
No database — every record lives in plain JSON files on disk, read and
written through a small set of Python utility functions.

## Features

- **Login** — User ID + password screen guards the whole app; nothing is
  accessible until you sign in.
- **Dashboard** with live stats (total/available/issued books, members,
  overdue loans, pending fines, recent activity)
- **Book catalogue**: add, edit, delete, search, filter, and view details
- **Member management**: register, edit, delete, search, filter, and view a
  member's active loans + full borrowing history
- **Issue Book**: eligibility checks (membership status, copy availability,
  per-member loan cap, duplicate active loan), automatic due-date calculation
- **Return Book**: automatic overdue detection and fine calculation
- **Transaction history** with Active / Overdue / Returned filters
- **Fines**: pending, paid, per-member breakdown, and "mark as paid"
- **Settings**: configurable borrowing period, fine rate, and loan cap
- **Collapsible sidebar** — hide the menu with the toggle button in the top
  bar for a wider working view; the choice is remembered on your next visit
- **Light / dark theme** — toggle with the sun/moon button; also remembered
  between visits

## Technology Stack

- **Backend:** Python 3 + Flask
- **Frontend:** HTML5, CSS3 (hand-written, no framework), vanilla JavaScript
- **Storage:** Local JSON files in `data/` — no database of any kind
- **Templating:** Jinja2 (via Flask)

## Project Structure

```
library_management_system/
│
├── app.py                  # All Flask routes
├── requirements.txt
├── README.md
│
├── data/                   # The "database" — plain JSON files
│   ├── books.json
│   ├── students.json
│   ├── transactions.json
│   ├── settings.json
│   └── users.json          # librarian login (hashed password)
│
├── utils/                  # Business logic, separated from routes
│   ├── json_utils.py       # generic read/write/CRUD for any JSON file
│   ├── auth.py             # login/password verification
│   ├── books.py            # book catalogue rules
│   ├── students.py         # member rules
│   ├── transactions.py     # issue/return/fine calculation
│   └── fines.py            # fine aggregation + dashboard stats
│
├── templates/               # Jinja2 templates
│   ├── base.html            # shared shell/sidebar/topbar/theme toggle
│   ├── login.html
│   ├── dashboard.html, books.html, book_form.html, book_detail.html
│   ├── students.html, student_form.html, student_detail.html
│   ├── issue_book.html, return_book.html
│   ├── transactions.html, fines.html, settings.html
│   └── 404.html, error.html
│
└── static/
    ├── css/style.css        # the whole visual design (incl. light/dark themes)
    └── js/script.js         # theme toggle, sidebar toggle, small UX helpers
```

## Installation & Running

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser. You'll land on the
sign-in screen — log in to reach the rest of the app.

**Demo credentials:** User ID `admin` · Password `library@123`

Data persists in the `data/*.json` files, so restarting the Flask server
never loses anything you've added, edited, issued, or returned.

## How the JSON Storage Works

`utils/json_utils.py` is the only place that touches the filesystem. It:
- reads a JSON file (returning `[]` if it's missing, and raising a clear
  error if it's corrupted, rather than crashing the app),
- writes a JSON file **atomically** (writes to a temp file, then swaps it
  into place) so a mid-write crash can never leave a half-written file,
- and exposes `add_record` / `update_record` / `delete_record` /
  `find_record` / `next_id` helpers that every other module builds on.

Every other module (`books.py`, `students.py`, `transactions.py`,
`fines.py`) only ever talks to the JSON files through those functions —
routes in `app.py` never touch `open()` directly.

## Default Configuration

| Setting | Default |
|---|---|
| Borrowing period | 14 days |
| Fine per overdue day | ₹5 |
| Max active loans per member | 5 |

All three are editable from **Settings** in the Librarian Desk.

## Sample Data

The app ships with 12 books, 6 members, and 17 transactions (a mix of
active, overdue, and returned loans, some with paid and unpaid fines) so
the dashboard and every page have something real to show on first run.

## Login

`data/users.json` stores one Librarian account with a hashed password
(`werkzeug.security`, never plaintext). Sign in with:

- **User ID:** `admin`
- **Password:** `library@123`

This is a single shared account for a local college project — there's no
registration flow or password reset. To change the password, generate a
new hash and paste it into `data/users.json`:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-new-password'))"
```

## Interface Options

- **Sidebar** — click the &#9776; icon in the top bar to hide or show the
  side menu; your choice is remembered (via the browser's local storage)
  the next time you open the app.
- **Theme** — click the sun/moon icon to switch between dark and light
  mode; also remembered between visits.

## Future Improvements

- Real authentication (hashed passwords) if this ever needs to be
  multi-user or internet-facing
- Book reservations / a waitlist for popular titles
- Email or SMS due-date reminders
- CSV export of transactions and fines for accounting
- Pagination for very large catalogues (current search/filter is fine for
  a few hundred books, but would want indexing at real library scale)
- Automated tests for the `utils/` business-logic layer
