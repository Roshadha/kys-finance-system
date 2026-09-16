from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
from datetime import UTC, date, datetime, timedelta
from contextlib import closing
from functools import wraps
from io import BytesIO
from pathlib import Path

import pandas as pd
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
db = SQLAlchemy()

TASKS = {
    "income_entry": "Income data entry",
    "expense_entry": "Expenditure data entry",
    "vat_entry": "VAT / tax data entry",
    "view_reports": "View reports",
}
ROLES = {"admin": "Administrator", "data_entry": "Data Entry", "management": "Management"}


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="data_entry")
    tasks_json = db.Column(db.Text, nullable=False, default="[]")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    @property
    def tasks(self):
        try:
            return json.loads(self.tasks_json)
        except (TypeError, json.JSONDecodeError):
            return []

    def can(self, task):
        return self.role == "admin" or task in self.tasks

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=True)
    kind = db.Column(db.String(20), nullable=False)
    group_name = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    service_line = db.Column(db.String(30), nullable=True)
    entity_name = db.Column(db.String(140), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(40), unique=True, nullable=False)
    registration_no = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(140), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cash_date = db.Column(db.Date, nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False, index=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=True)
    reference = db.Column(db.String(80), nullable=False)
    counterparty = db.Column(db.String(140), nullable=False)
    description = db.Column(db.String(240), nullable=True)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    sscl = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    vat = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    category = db.relationship("Category")
    vehicle = db.relationship("Vehicle", backref=db.backref("transactions", lazy=True))
    created_by = db.relationship("User")
    adjustments = db.relationship("Adjustment", backref="transaction", lazy=True)

    @property
    def adjustment_total(self):
        return sum(float(item.amount) for item in self.adjustments)

    @property
    def adjusted_total(self):
        return float(self.total) + self.adjustment_total


class Adjustment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transaction.id"), nullable=False, index=True)
    effective_date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    reason = db.Column(db.String(240), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    created_by = db.relationship("User")


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    happened_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    user = db.relationship("User")


def create_app(test_config=None):
    app = Flask(__name__)
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    secret_file = data_dir / ".secret_key"
    if os.environ.get("KYS_SECRET_KEY"):
        secret_key = os.environ["KYS_SECRET_KEY"]
    elif secret_file.exists():
        secret_key = secret_file.read_text(encoding="utf-8").strip()
    else:
        secret_key = secrets.token_hex(32)
        secret_file.write_text(secret_key, encoding="utf-8")
    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "KYS_DATABASE_URL", f"sqlite:///{(BASE_DIR / 'data' / 'kys_finance.db').as_posix()}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    (BASE_DIR / "backups").mkdir(exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_database()

    register_routes(app)
    register_context(app)

    if not app.config.get("TESTING") and os.environ.get("KYS_DISABLE_BACKUP", "0") != "1":
        start_backup_worker(app)
    return app


def audit(action, entity_type, entity_id=None, details=""):
    db.session.add(AuditLog(
        user_id=session.get("user_id"), action=action, entity_type=entity_type,
        entity_id=entity_id, details=details,
    ))


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user.active:
            session.clear()
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user().role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def task_required(task):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user().can(task):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def parse_date(value, fallback=None):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return fallback


def parse_money(value):
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        raise ValueError("Enter a valid amount.")


def period_from_request():
    today = date.today()
    start_default = today.replace(day=1)
    next_month = (start_default.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_default = next_month - timedelta(days=1)
    start = parse_date(request.args.get("start"), start_default)
    end = parse_date(request.args.get("end"), end_default)
    if start > end:
        start, end = end, start
    return start, end


def base_transactions(start, end):
    return (
        Transaction.query.join(Category)
        .filter(Transaction.cash_date.between(start, end))
        .order_by(Transaction.cash_date, Transaction.id)
        .all()
    )


def build_report(start, end, report_type="monthly"):
    txns = base_transactions(start, end)
    filtered = []
    for txn in txns:
        c = txn.category
        if report_type == "direct" and not c.service_line:
            continue
        if report_type == "rental" and not c.entity_name:
            continue
        if report_type == "construction" and "Construction" not in c.group_name:
            continue
        filtered.append(txn)

    rows = []
    for txn in filtered:
        c = txn.category
        adjusted = txn.adjusted_total
        rows.append({
            "Date": txn.cash_date.isoformat(),
            "Reference": txn.reference,
            "Type": c.kind.title(),
            "Group": c.group_name,
            "Account Code": c.code or "—",
            "Particular": c.name,
            "Service / Property": c.service_line or c.entity_name or "—",
            "Counterparty": txn.counterparty,
            "Subtotal": float(txn.subtotal),
            "SSCL": float(txn.sscl),
            "VAT": float(txn.vat),
            "Original Total": float(txn.total),
            "Adjustments": txn.adjustment_total,
            "Cash Total": adjusted,
        })

    income = sum(r["Cash Total"] for r in rows if r["Type"] == "Income")
    expense = sum(r["Cash Total"] for r in rows if r["Type"] == "Expense")
    grouped = {}
    for row in rows:
        if report_type == "direct":
            key = row["Service / Property"]
        elif report_type == "rental":
            key = row["Service / Property"]
        else:
            key = row["Group"]
        grouped.setdefault(key, {"income": 0.0, "expense": 0.0})
        grouped[key][row["Type"].lower()] += row["Cash Total"]
    summary = [
        {"label": key, **values, "pl": values["income"] - values["expense"]}
        for key, values in sorted(grouped.items())
    ]
    return {"rows": rows, "summary": summary, "income": income, "expense": expense, "pl": income - expense}


def export_report_xlsx(start, end, report_type):
    data = build_report(start, end, report_type)
    output = BytesIO()
    title_map = {
        "monthly": "Monthly Cash-Based P&L",
        "short": "Short Summary P&L",
        "direct": "Direct Trade P&L",
        "rental": "Rented Building P&L",
        "construction": "Construction Projects P&L",
    }
    summary_rows = [{
        "Particular": item["label"], "Income": item["income"],
        "Expenditure": item["expense"], "Liquid P/L": item["pl"],
    } for item in data["summary"]]
    summary_rows.append({
        "Particular": "TOTAL", "Income": data["income"],
        "Expenditure": data["expense"], "Liquid P/L": data["pl"],
    })
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False, startrow=4)
        if report_type != "short":
            pd.DataFrame(data["rows"]).to_excel(writer, sheet_name="Detailed Ledger", index=False, startrow=4)
        for ws in writer.book.worksheets:
            ws["A1"] = "K.Y.S. Cash-Based P&L Management System"
            ws["A2"] = title_map.get(report_type, title_map["monthly"])
            ws["A3"] = f"Cash period: {start:%d %b %Y} to {end:%d %b %Y}"
            ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
            ws["A1"].fill = PatternFill("solid", fgColor="0D3B34")
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(ws.max_column, 4))
            ws["A2"].font = Font(size=12, bold=True, color="163C34")
            header_fill = PatternFill("solid", fgColor="DCEBE6")
            thin = Side(style="thin", color="D6E0DC")
            for cell in ws[5]:
                cell.font = Font(bold=True, color="163C34")
                cell.fill = header_fill
                cell.border = Border(bottom=thin)
                cell.alignment = Alignment(vertical="center")
            ws.freeze_panes = "A6"
            ws.auto_filter.ref = f"A5:{ws.cell(5, ws.max_column).column_letter}{ws.max_row}"
            for column_index, column in enumerate(ws.iter_cols(), start=1):
                letter = get_column_letter(column_index)
                max_len = max(len(str(cell.value or "")) for cell in column)
                ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 42)
            for row in ws.iter_rows(min_row=6):
                for cell in row:
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = '#,##0.00;[Red]-#,##0.00'
    output.seek(0)
    return output


def register_context(app):
    @app.context_processor
    def shared():
        return {
            "current_user": current_user(), "TASKS": TASKS, "ROLES": ROLES,
            "today": date.today(), "csrf_token": session.get("csrf_token", ""),
        }

    @app.template_filter("money")
    def money(value):
        return f"{float(value or 0):,.2f}"

    @app.before_request
    def csrf_and_session():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        if request.method == "POST":
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not secrets.compare_digest(token or "", session.get("csrf_token", "")):
                abort(400, "Invalid or expired form token. Refresh the page and try again.")


def register_routes(app):
    @app.get("/health")
    def health():
        return {"status": "ok", "database": "connected"}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            user = User.query.filter(func.lower(User.username) == username.lower()).first()
            if user and user.active and check_password_hash(user.password_hash, request.form.get("password", "")):
                session.clear()
                session["user_id"] = user.id
                session["csrf_token"] = secrets.token_urlsafe(24)
                audit("login", "user", user.id, "Successful sign in")
                db.session.commit()
                return redirect(request.args.get("next") or url_for("dashboard"))
            flash("The username or password is incorrect.", "error")
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        uid = current_user().id
        audit("logout", "user", uid, "Signed out")
        db.session.commit()
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def dashboard():
        today = date.today()
        start = today.replace(day=1)
        data = build_report(start, today, "monthly")
        recent = Transaction.query.order_by(Transaction.created_at.desc()).limit(7).all()
        monthly = []
        for offset in range(5, -1, -1):
            month = (today.replace(day=1) - timedelta(days=offset * 28)).replace(day=1)
            nxt = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
            report = build_report(month, nxt - timedelta(days=1), "monthly")
            monthly.append({"label": month.strftime("%b"), **report})
        return render_template("dashboard.html", data=data, recent=recent, monthly=monthly)

    @app.get("/transactions")
    @login_required
    def transactions():
        start, end = period_from_request()
        kind = request.args.get("kind", "")
        query = Transaction.query.join(Category).filter(Transaction.cash_date.between(start, end))
        if kind in {"income", "expense"}:
            query = query.filter(Category.kind == kind)
        items = query.order_by(Transaction.cash_date.desc(), Transaction.id.desc()).all()
        return render_template("transactions.html", items=items, start=start, end=end, kind=kind)

    @app.route("/transactions/new", methods=["GET", "POST"])
    @login_required
    def transaction_new():
        requested_kind = request.args.get("kind", request.form.get("kind", "income"))
        if requested_kind not in {"income", "expense"}:
            requested_kind = "income"
        task = "income_entry" if requested_kind == "income" else "expense_entry"
        if not current_user().can(task):
            abort(403)
        categories = Category.query.filter_by(kind=requested_kind, active=True).order_by(Category.group_name, Category.name).all()
        vehicles = Vehicle.query.filter_by(active=True).order_by(Vehicle.identifier).all()
        if request.method == "POST":
            try:
                category = db.session.get(Category, int(request.form.get("category_id", 0)))
                if not category or category.kind != requested_kind:
                    raise ValueError("Select a valid account.")
                cash_date = parse_date(request.form.get("cash_date"))
                if not cash_date:
                    raise ValueError("Select the actual cash date.")
                subtotal = parse_money(request.form.get("subtotal"))
                sscl = parse_money(request.form.get("sscl"))
                vat = parse_money(request.form.get("vat"))
                total = round(subtotal + sscl + vat, 2)
                if total <= 0:
                    raise ValueError("Grand total must be greater than zero.")
                reference = request.form.get("reference", "").strip()
                counterparty = request.form.get("counterparty", "").strip()
                if not reference or not counterparty:
                    raise ValueError("Reference and counterparty are required.")
                vehicle_id = request.form.get("vehicle_id") or None
                if "Vehicle Running" in category.name and not vehicle_id:
                    raise ValueError("Choose the vehicle for this maintenance entry.")
                item = Transaction(
                    cash_date=cash_date, category_id=category.id, vehicle_id=int(vehicle_id) if vehicle_id else None,
                    reference=reference, counterparty=counterparty,
                    description=request.form.get("description", "").strip(), subtotal=subtotal,
                    sscl=sscl, vat=vat, total=total, created_by_id=current_user().id,
                )
                db.session.add(item)
                db.session.flush()
                audit("create", "transaction", item.id, f"{requested_kind} {total:.2f} / {reference}")
                db.session.commit()
                flash(f"Cash {requested_kind} saved. The ledger entry is now locked.", "success")
                return redirect(url_for("transactions"))
            except (ValueError, TypeError) as exc:
                db.session.rollback()
                flash(str(exc), "error")
        return render_template("transaction_form.html", kind=requested_kind, categories=categories, vehicles=vehicles)

    @app.route("/transactions/<int:transaction_id>/adjust", methods=["GET", "POST"])
    @role_required("admin")
    def adjustment_new(transaction_id):
        txn = db.get_or_404(Transaction, transaction_id)
        if request.method == "POST":
            try:
                amount = parse_money(request.form.get("amount"))
                reason = request.form.get("reason", "").strip()
                effective_date = parse_date(request.form.get("effective_date"))
                if amount == 0 or not reason or not effective_date:
                    raise ValueError("Date, a non-zero adjustment, and a reason are required.")
                adj = Adjustment(
                    transaction_id=txn.id, effective_date=effective_date, amount=amount,
                    reason=reason, created_by_id=current_user().id,
                )
                db.session.add(adj)
                db.session.flush()
                audit("adjust", "transaction", txn.id, f"Adjustment {amount:.2f}: {reason}")
                db.session.commit()
                flash("Adjustment posted. The original entry remains unchanged.", "success")
                return redirect(url_for("transactions"))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), "error")
        return render_template("adjustment_form.html", txn=txn)

    @app.get("/reports")
    @task_required("view_reports")
    def reports():
        start, end = period_from_request()
        report_type = request.args.get("type", "monthly")
        if report_type not in {"monthly", "short", "direct", "rental", "construction"}:
            report_type = "monthly"
        data = build_report(start, end, report_type)
        return render_template("reports.html", data=data, start=start, end=end, report_type=report_type)

    @app.get("/reports/export")
    @task_required("view_reports")
    def reports_export():
        start, end = period_from_request()
        report_type = request.args.get("type", "monthly")
        if report_type not in {"monthly", "short", "direct", "rental", "construction"}:
            report_type = "monthly"
        output = export_report_xlsx(start, end, report_type)
        audit("export", "report", None, f"{report_type}: {start} to {end}")
        db.session.commit()
        return send_file(
            output, as_attachment=True,
            download_name=f"KYS_{report_type}_PL_{start}_{end}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.get("/history")
    @role_required("admin")
    def history():
        logs = AuditLog.query.order_by(AuditLog.happened_at.desc()).limit(300).all()
        return render_template("history.html", logs=logs)

    @app.get("/users")
    @role_required("admin")
    def users():
        return render_template("users.html", users=User.query.order_by(User.active.desc(), User.display_name).all())

    @app.route("/users/new", methods=["GET", "POST"])
    @role_required("admin")
    def user_new():
        if request.method == "POST":
            try:
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "")
                role = request.form.get("role", "data_entry")
                if not username or len(password) < 8 or role not in ROLES:
                    raise ValueError("Use a username, valid role, and password of at least 8 characters.")
                if User.query.filter(func.lower(User.username) == username.lower()).first():
                    raise ValueError("That username is already in use.")
                user = User(
                    username=username,
                    display_name=request.form.get("display_name", "").strip() or username,
                    department=request.form.get("department", "").strip(), role=role,
                    tasks_json=json.dumps(request.form.getlist("tasks")),
                )
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                audit("create", "user", user.id, f"Created {username} as {role}")
                db.session.commit()
                flash("User account created.", "success")
                return redirect(url_for("users"))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), "error")
        return render_template("user_form.html")

    @app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
    @role_required("admin")
    def user_edit(user_id):
        user = db.get_or_404(User, user_id)
        if request.method == "POST":
            role = request.form.get("role", "data_entry")
            password = request.form.get("password", "")
            if role not in ROLES:
                flash("Select a valid role.", "error")
            elif password and len(password) < 8:
                flash("A reset password must be at least 8 characters.", "error")
            else:
                user.display_name = request.form.get("display_name", "").strip() or user.username
                user.department = request.form.get("department", "").strip()
                user.role = role
                user.tasks_json = json.dumps(request.form.getlist("tasks"))
                if password:
                    user.set_password(password)
                audit("update", "user", user.id, f"Role/tasks updated for {user.username}")
                db.session.commit()
                flash("User role and task assignments updated.", "success")
                return redirect(url_for("users"))
        return render_template("user_form.html", edit_user=user)

    @app.post("/users/<int:user_id>/toggle")
    @role_required("admin")
    def user_toggle(user_id):
        user = db.get_or_404(User, user_id)
        if user.id == current_user().id:
            flash("You cannot disable your own signed-in account.", "error")
        else:
            user.active = not user.active
            audit("status", "user", user.id, f"Active: {user.active}")
            db.session.commit()
            flash("User access updated.", "success")
        return redirect(url_for("users"))

    @app.get("/vehicles")
    @role_required("admin")
    def vehicles():
        return render_template("vehicles.html", vehicles=Vehicle.query.order_by(Vehicle.identifier).all())

    @app.get("/categories")
    @role_required("admin")
    def categories():
        items = Category.query.order_by(Category.kind, Category.group_name, Category.code, Category.name).all()
        return render_template("categories.html", categories=items)

    @app.post("/categories")
    @role_required("admin")
    def category_new():
        kind = request.form.get("kind", "")
        group_name = request.form.get("group_name", "").strip()
        name = request.form.get("name", "").strip()
        if kind not in {"income", "expense"} or not group_name or not name:
            flash("Type, group, and particular name are required.", "error")
        else:
            item = Category(
                code=request.form.get("code", "").strip() or None, kind=kind,
                group_name=group_name, name=name,
                service_line=request.form.get("service_line", "").strip() or None,
                entity_name=request.form.get("entity_name", "").strip() or None,
            )
            db.session.add(item)
            db.session.flush()
            audit("create", "category", item.id, f"{kind}: {name}")
            db.session.commit()
            flash("Account particular added.", "success")
        return redirect(url_for("categories"))

    @app.post("/categories/<int:category_id>/toggle")
    @role_required("admin")
    def category_toggle(category_id):
        item = db.get_or_404(Category, category_id)
        item.active = not item.active
        audit("status", "category", item.id, f"Active: {item.active}")
        db.session.commit()
        flash("Account availability updated.", "success")
        return redirect(url_for("categories"))

    @app.post("/vehicles")
    @role_required("admin")
    def vehicle_new():
        identifier = request.form.get("identifier", "").strip()
        if not identifier:
            flash("Vehicle identifier is required.", "error")
        elif Vehicle.query.filter(func.lower(Vehicle.identifier) == identifier.lower()).first():
            flash("That vehicle identifier already exists.", "error")
        else:
            vehicle = Vehicle(
                identifier=identifier,
                registration_no=request.form.get("registration_no", "").strip(),
                description=request.form.get("description", "").strip(),
            )
            db.session.add(vehicle)
            db.session.flush()
            audit("create", "vehicle", vehicle.id, identifier)
            db.session.commit()
            flash("Vehicle added.", "success")
        return redirect(url_for("vehicles"))

    @app.post("/backup")
    @role_required("admin")
    def backup_now():
        path = make_backup(app)
        audit("backup", "database", None, path.name)
        db.session.commit()
        flash(f"Backup created: {path.name}", "success")
        return redirect(url_for("dashboard"))

    @app.route("/account/password", methods=["GET", "POST"])
    @login_required
    def change_password():
        user = current_user()
        if request.method == "POST":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            if not check_password_hash(user.password_hash, current):
                flash("Current password is incorrect.", "error")
            elif len(new) < 8:
                flash("New password must be at least 8 characters.", "error")
            else:
                user.set_password(new)
                audit("password", "user", user.id, "Password changed")
                db.session.commit()
                flash("Password updated.", "success")
                return redirect(url_for("dashboard"))
        return render_template("change_password.html")

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, message="You do not have permission to open this area."), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="The requested record or page was not found."), 404


def make_backup(app):
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not database_uri.startswith("sqlite:///"):
        raise RuntimeError("Automatic file backup is only available for SQLite.")
    source = Path(database_uri.removeprefix("sqlite:///"))
    if not source.is_absolute():
        source = BASE_DIR / source
    destination = BASE_DIR / "backups" / f"kys_finance_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    temporary = destination.with_suffix(".tmp")
    destination.parent.mkdir(exist_ok=True)
    with closing(sqlite3.connect(source)) as source_db, closing(sqlite3.connect(temporary)) as backup_db:
        source_db.backup(backup_db)
    temporary.replace(destination)
    backups = sorted(destination.parent.glob("kys_finance_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[60:]:
        old.unlink(missing_ok=True)
    return destination


def start_backup_worker(app):
    if getattr(app, "_backup_started", False):
        return
    app._backup_started = True

    def worker():
        while True:
            time.sleep(2 * 60 * 60)
            try:
                make_backup(app)
            except Exception:
                app.logger.exception("Scheduled backup failed")

    threading.Thread(target=worker, daemon=True, name="sqlite-backup").start()


def seed_database():
    if not User.query.first():
        defaults = [
            ("admin", "System Administrator", "Accounts", "admin", [*TASKS], "Admin@2026"),
            ("management", "Management", "Management", "management", ["view_reports"], "Manage@2026"),
            ("recovery", "Recovery Department", "Recovery", "data_entry", ["income_entry", "vat_entry"], "KysRec@2026"),
        ]
        for username, display, department, role, tasks, password in defaults:
            user = User(username=username, display_name=display, department=department, role=role, tasks_json=json.dumps(tasks))
            user.set_password(password)
            db.session.add(user)

    if not Category.query.first():
        categories = []
        def add(code, kind, group, name, service=None, entity=None):
            categories.append(Category(code=str(code) if code else None, kind=kind, group_name=group, name=name, service_line=service, entity_name=entity))

        add(351, "income", "Trade Income", "Security Service Income", "Security")
        add(352, "income", "Trade Income", "Cleaning Service Income", "Cleaning")
        add(201, "income", "Bank Interest Income", "Bank Interest Received")
        rentals = [
            (353, "K.Y.S. Auto Service"), (354, "Pinarawa Housing Complex"), (355, "Welekade Shops"),
            (355, "Ratwatta Guest House"), (356, "2nd Mile Post Shop Complex"), (356, "Chandrasiri House"),
            (357, "MD Home Upper Stairs"), (357, "MD Home Shop"), (358, "Haputhale Hotel"),
            (363, "2nd Mile Post Hostel"), (364, "Galaxy - A Hostel"), (364, "Galaxy - E Hostel"),
            (365, "Pihillakade Housing Complex"), (366, "Vineethagama House"),
        ]
        for code, entity in rentals:
            add(code, "income", "Rental Income", f"{entity} Rent Income", entity=entity)
        add(None, "income", "Construction Projects Income", "Construction Project Receipt")

        for code, name, service in [
            (451, "Security Service Salary", "Security"), (452, "Security Service EPF 12%", "Security"),
            (453, "Security Service ETF 3%", "Security"), (451, "Cleaning Service Salary", "Cleaning"),
            (452, "Cleaning Service EPF 12%", "Cleaning"), (453, "Cleaning Service ETF 3%", "Cleaning"),
        ]:
            add(code, "expense", "Direct Trade Expenditure", name, service)
        operational = [
            (451, "Staff Salary Expenditure"), (452, "EPF (12%) Expenditure"), (453, "ETF (3%) Expenditure"),
            (501, "Office Expenditure"), (502, "Printing & Stationery Expenditure"), (503, "Postage & Courier Expenditure"),
            (504, "Travelling & Subsistence Expenditure"), (505, "Service Operation Expenditure"),
            (506, "Vehicle Running & Maintenance Expenditure"), (507, "Security Items Expenditure"),
            (508, "Cleaning Items & Materials Expenditure"), (509, "Training, Permit, Licence & Miscellaneous Expenditure"),
            (510, "Tender Documents Expenditure"), (513, "Charity & Donation Expenditure"),
            (514, "Marketing, Promotion, Subscription & Periodicals Expenditure"), (515, "Professional Fees Expenditure"),
            (516, "Staff Training & Programme Expenditure"), (520, "Cleaning Service Other Expenditure"),
            (551, "Electricity Charges Expenditure"), (552, "Water Supply Charges Expenditure"),
            (553, "Telephone & Internet Charges Expenditure"), (609, "MD House Expenditure"),
            (612, "Kottawa Prime Residence Expenditure"), (652, "Personal Insurance Premium Expenditure"),
            (653, "Employees Insurance Premium Expenditure"), (654, "Vehicle & General Insurance Premium Expenditure"),
            (655, "Financial / Loan & OD Interest Expenditure"),
        ]
        for code, name in operational:
            add(code, "expense", "Operational Expenditure", name)
        maintenance_codes = {"K.Y.S. Auto Service": 601, "Pinarawa Housing Complex": 602, "Welekade Shops": 603,
            "Ratwatta Guest House": 603, "2nd Mile Post Shop Complex": 604, "Chandrasiri House": 604,
            "MD Home Upper Stairs": 605, "MD Home Shop": 605, "Haputhale Hotel": None,
            "2nd Mile Post Hostel": 613, "Galaxy - A Hostel": 616, "Galaxy - E Hostel": 616,
            "Pihillakade Housing Complex": None, "Vineethagama House": 611}
        for entity, code in maintenance_codes.items():
            add(code, "expense", "Maintenance Expenditure", f"{entity} Maintenance & Expenditure", entity=entity)
        add(None, "expense", "Construction Projects Expenditure", "Construction Project Payment")
        investments = [
            (608, "WIP Velaudam Land Building Investment - Phase I"), (620, "WIP Velaudam Land Building Investment - Phase II"),
            (610, "WIP Damanwara St. Bernard Tea Plantation Investment"), (662, "WIP Damanwara St. Bernard Land Development Investment"),
            (661, "WIP Galaxy A & E Hostel Building Investment"), (630, "WIP Pihillakade Housing Complex Investment"),
            (635, "WIP Kandana Pepper Cultivation Investment"),
        ]
        for code, name in investments:
            add(code, "expense", "Investment Projects Expenditure", name)
        db.session.add_all(categories)

    if not Vehicle.query.first():
        db.session.add_all([
            Vehicle(identifier="A", description="Vehicle A"),
            Vehicle(identifier="B", description="Vehicle B"),
            Vehicle(identifier="C", description="Vehicle C"),
        ])
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
