from flask import Flask, request, redirect, render_template, flash, url_for
import sqlite3
from pathlib import Path
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deployment"
BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "expenses.db"
CATEGORIES = ["Food", "Travel", "Education", "Shopping", "Salary", "Bills", "Health", "Entertainment", "Other"]


def get_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                kind TEXT NOT NULL CHECK(kind IN ('Income', 'Expense')),
                category TEXT NOT NULL,
                date TEXT NOT NULL
            )
        """)


def validate_transaction(form):
    title = form.get("title", "").strip()
    category = form.get("category", "Other").strip()
    kind = form.get("kind", "").strip()
    transaction_date = form.get("date", "").strip()
    try:
        amount = float(form.get("amount", "0"))
    except (TypeError, ValueError):
        return None, "Please enter a valid amount."

    if not title or len(title) > 100:
        return None, "Description must be between 1 and 100 characters."
    if amount <= 0:
        return None, "Amount must be greater than zero."
    if kind not in ("Income", "Expense"):
        return None, "Choose Income or Expense."
    if category not in CATEGORIES:
        return None, "Choose a valid category."
    try:
        datetime.strptime(transaction_date, "%Y-%m-%d")
    except ValueError:
        return None, "Choose a valid date."
    return (title, amount, kind, category, transaction_date), None


@app.route("/")
def home():
    with get_db() as con:
        transactions = con.execute(
            "SELECT * FROM transactions ORDER BY date DESC, id DESC"
        ).fetchall()
        totals = con.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN kind='Income' THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN kind='Expense' THEN amount ELSE 0 END), 0) AS expense
            FROM transactions
        """).fetchone()
        category_rows = con.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE kind='Expense'
            GROUP BY category
            ORDER BY total DESC
        """).fetchall()

    income = totals["income"]
    expense = totals["expense"]
    return render_template(
        "dashboard.html",
        transactions=transactions,
        income=income,
        expense=expense,
        balance=income-expense,
        today=date.today().isoformat(),
        categories=CATEGORIES,
        category_labels=[r["category"] for r in category_rows],
        category_values=[r["total"] for r in category_rows],
    )


@app.route("/add", methods=["POST"])
def add():
    values, error = validate_transaction(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("home"))
    with get_db() as con:
        con.execute(
            """INSERT INTO transactions (title, amount, kind, category, date)
               VALUES (?, ?, ?, ?, ?)""",
            values
        )
    flash("Transaction added successfully.", "success")
    return redirect(url_for("home"))


@app.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit(transaction_id):
    with get_db() as con:
        transaction = con.execute(
            "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()

        if transaction is None:
            flash("Transaction not found.", "error")
            return redirect(url_for("home"))

        if request.method == "POST":
            values, error = validate_transaction(request.form)
            if error:
                flash(error, "error")
                return redirect(url_for("edit", transaction_id=transaction_id))
            con.execute("""
                UPDATE transactions
                SET title=?, amount=?, kind=?, category=?, date=?
                WHERE id=?
            """, (*values, transaction_id))
            flash("Transaction updated successfully.", "success")
            return redirect(url_for("home"))

    return render_template("edit.html", transaction=transaction, categories=CATEGORIES)


@app.route("/delete/<int:transaction_id>", methods=["POST"])
def delete(transaction_id):
    with get_db() as con:
        cursor = con.execute(
            "DELETE FROM transactions WHERE id = ?", (transaction_id,)
        )
    if cursor.rowcount:
        flash("Transaction deleted.", "success")
    else:
        flash("Transaction not found.", "error")
    return redirect(url_for("home"))


@app.route("/reports")
def reports():
    with get_db() as con:
        monthly = con.execute("""
            SELECT substr(date, 1, 7) AS month,
                   SUM(CASE WHEN kind='Income' THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN kind='Expense' THEN amount ELSE 0 END) AS expense
            FROM transactions
            GROUP BY substr(date, 1, 7)
            ORDER BY month
        """).fetchall()
        categories = con.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions WHERE kind='Expense'
            GROUP BY category ORDER BY total DESC
        """).fetchall()
    return render_template("reports.html", monthly=monthly, categories=categories)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
