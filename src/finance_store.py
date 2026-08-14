import sqlite3
from datetime import datetime
from src.user_scope import resolve_database_path

DEFAULT_LIMITS = {"alimentação": 450.0, "lazer": 200.0, "transporte": 180.0, "compras": 250.0}

def _connect():
    conn = sqlite3.connect(resolve_database_path()); conn.row_factory = sqlite3.Row; return conn

def init_finance_tables():
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS finance_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL, description TEXT, occurred_on TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS finance_limits (category TEXT PRIMARY KEY, monthly_limit REAL NOT NULL);
        """)
        for category, limit in DEFAULT_LIMITS.items():
            conn.execute("INSERT OR IGNORE INTO finance_limits(category, monthly_limit) VALUES (?, ?)", (category, limit))

def add_entry(kind, amount, category, description=None):
    with _connect() as conn:
        conn.execute("INSERT INTO finance_entries(kind, amount, category, description, occurred_on, created_at) VALUES (?, ?, ?, ?, ?, ?)", (kind, amount, category.lower().strip(), description, datetime.now().date().isoformat(), datetime.now().isoformat(timespec='seconds')))

def month_report(year=None, month=None):
    now=datetime.now(); year=year or now.year; month=month or now.month; prefix=f"{year:04d}-{month:02d}"
    with _connect() as conn:
        rows=conn.execute("SELECT kind, category, SUM(amount) total FROM finance_entries WHERE occurred_on LIKE ? GROUP BY kind, category", (prefix+'%',)).fetchall()
        limits={r['category']:float(r['monthly_limit']) for r in conn.execute("SELECT category, monthly_limit FROM finance_limits")}
    income=sum(float(r['total']) for r in rows if r['kind']=='entrada'); expenses=sum(float(r['total']) for r in rows if r['kind']=='saida')
    categories={r['category']:float(r['total']) for r in rows if r['kind']=='saida'}
    return income, expenses, income-expenses, categories, limits

def previous_month_report():
    now=datetime.now(); year, month=now.year, now.month-1
    if month==0: year-=1; month=12
    return month_report(year, month)
