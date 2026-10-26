from __future__ import annotations

import json
import hashlib
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from contextlib import closing
from collections import deque
from functools import wraps
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from flask import (
    Flask,
    abort,
    flash,
    g,
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
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.schema import CreateIndex, CreateTable
from werkzeug.security import check_password_hash, generate_password_hash
from account_catalog import GROUPS as CATALOG_GROUPS, PARTICULARS as CATALOG_PARTICULARS
from backup_settings import read_settings, save_settings, read_status, record_status
from release_info import VERSION


BASE_DIR = Path(__file__).resolve().parent
# Bundled templates/static live inside PyInstaller's resource folder, while
# user data must remain beside the executable across upgrades and restarts.
DATA_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else BASE_DIR
db = SQLAlchemy()
BACKUP_LOCK = threading.Lock()


def serialized_backup(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not BACKUP_LOCK.acquire(timeout=45):
            raise RuntimeError('Another backup is still running. Please retry later.')
        try:
            return function(*args, **kwargs)
        finally:
            BACKUP_LOCK.release()
    return wrapped

TASKS = {
    "income_entry": "Income data entry",
    "expense_entry": "Expenditure data entry",
    "vat_entry": "VAT / tax data entry",
    "view_reports": "View reports",
    "delete_entries": "Delete ledger entries",
    "edit_entries": "Edit ledger entries",
}
ROLES = {"admin": "Administrator", "data_entry": "Data Entry", "management": "Management"}
SUBTOTAL_ONLY_GROUPS = {
    ("income", "Trade Income"),
    ("income", "Inward Taxes"),
    ("expense", "Tax Expenditure"),
    ("expense", "Outward Taxes"),
}

# Only unambiguous legacy labels are renamed automatically. A posted account
# without a match blocks the import so staff can choose its destination first.
CATALOG_ALIASES = {
    ('income', 'Property Rental Income'): ('Rental Income',),
    ('income', 'Welekade Shops Rental Income'): ('Welekade Shops Rent Income',),
    ('income', 'Galaxy - A Hostel Rental Income'): ('Galaxy - A Hostel Rent Income',),
    ('expense', 'Property Maintenance Expenditure'): ('Maintenance Expenditure',),
    ('expense', 'Staff Training Programme Expenditure'): ('Staff Training & Programme Expenditure',),
    ('expense', 'Cleaning Items, Materials & Equipment Expenditure'):
        ('Cleaning Items & Materials Expenditure',),
    ('expense', 'Construction Projects Expenditure 1'): ('Construction Projects Expenditure',),
}


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="data_entry")
    tasks_json = db.Column(db.Text, nullable=False, default="[]")
    active = db.Column(db.Boolean, nullable=False, default=True)
    deleted = db.Column(db.Boolean, nullable=False, default=False)
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


# Primary keys double as the visible codes.
# Groups: IG_100, IG_200 ... (income) and EG_100, EG_200 ... (expenditure), +100 each.
# Particulars: IP_0010, IP_0020 ... (income) and EP_0010, EP_0020 ... (expenditure), +10 each.
GROUP_PREFIX = {"income": "IG", "expense": "EG"}
CATEGORY_PREFIX = {"income": "IP", "expense": "EP"}
ID_RULES = {"Group": (GROUP_PREFIX, 100, 0), "Category": (CATEGORY_PREFIX, 10, 4)}


class Group(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    kind = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint("kind", "name", name="uq_group_kind_name"),)


class Category(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    group_id = db.Column(db.String(20), db.ForeignKey("group.id"), nullable=True, index=True)
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
    category_id = db.Column(db.String(20), db.ForeignKey("category.id"), nullable=False, index=True)
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
        return sum((item.amount for item in self.adjustments), Decimal('0.00'))

    @property
    def adjusted_total(self):
        return self.total + self.adjustment_total


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
    entity_id = db.Column(db.String(40), nullable=True)
    details = db.Column(db.Text, nullable=True)
    user = db.relationship("User")


def format_id(prefix, number, width):
    return f"{prefix}_{number:0{width}d}"


def highest_id_number(session, model, prefix):
    top = 0
    for (value,) in session.execute(select(model.id)):
        head, _, tail = str(value).partition("_")
        if head == prefix and tail.isdigit():
            top = max(top, int(tail))
    return top


@event.listens_for(Session, "before_flush")
def assign_account_ids(session, flush_context, instances):
    """Give every new group / particular the next code for its type."""
    for model in (Group, Category):
        pending = [obj for obj in session.new if isinstance(obj, model) and not obj.id]
        if not pending:
            continue
        prefixes, step, width = ID_RULES[model.__name__]
        tops = {}
        for obj in pending:
            prefix = prefixes[obj.kind]
            if prefix not in tops:
                with session.no_autoflush:
                    tops[prefix] = highest_id_number(session, model, prefix)
                for other in session.new:
                    if isinstance(other, model) and other.id:
                        head, _, tail = str(other.id).partition("_")
                        if head == prefix and tail.isdigit():
                            tops[prefix] = max(tops[prefix], int(tail))
            tops[prefix] += step
            obj.id = format_id(prefix, tops[prefix], width)


# Order used to number groups of databases created before group IDs existed.
LEGACY_GROUP_ORDER = [
    ("income", "Trade Income"), ("income", "Bank Interest Income"), ("income", "Rental Income"),
    ("income", "Construction Projects Income"), ("expense", "Direct Trade Expenditure"),
    ("expense", "Operational Expenditure"), ("expense", "Maintenance Expenditure"),
    ("expense", "Construction Projects Expenditure"), ("expense", "Investment Projects Expenditure"),
    ("income", "Inward Taxes"), ("expense", "Tax Expenditure"),
]


def numeric_part(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


def migrate_integer_ids(engine, backup_directory=None):
    from schema_migrations import migrate_legacy_ids
    tables = {model.__tablename__: model.__table__ for model in (Group, Category, Transaction, AuditLog)}
    return migrate_legacy_ids(engine, backup_directory or DATA_ROOT / 'backups', tables,
                              LEGACY_GROUP_ORDER, create_table=CreateTable)


def create_app(test_config=None):
    app = Flask(__name__)
    data_dir = DATA_ROOT / "data"
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
            "KYS_DATABASE_URL", f"sqlite:///{(DATA_ROOT / 'data' / 'kys_finance.db').as_posix()}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    if test_config:
        app.config.update(test_config)
    (DATA_ROOT / "backups").mkdir(exist_ok=True)
    db.init_app(app)

    with app.app_context():
        if db.engine.dialect.name == 'sqlite':
            @event.listens_for(db.engine, 'connect')
            def sqlite_policy(connection, _record):
                cursor = connection.cursor()
                try:
                    cursor.execute('PRAGMA busy_timeout=10000')
                    cursor.execute('PRAGMA synchronous=FULL')
                finally:
                    cursor.close()
            with db.engine.connect() as connection:
                if connection.exec_driver_sql('PRAGMA user_version').scalar() > 1:
                    raise RuntimeError('Database requires a newer server. Do not downgrade this installation.')
                connection.exec_driver_sql('PRAGMA journal_mode=WAL')
        migrate_integer_ids(db.engine, app.config.get("MIGRATION_BACKUP_DIR"))
        db.create_all()
        # Existing company databases predate account deletion. Retain their
        # user rows so ledger and audit foreign keys never lose attribution.
        if "deleted" not in {column["name"] for column in inspect(db.engine).get_columns("user")}:
            db_path = db.engine.url.database
            if db.engine.dialect.name == "sqlite" and db_path and db_path != ":memory:":
                backup_dir = Path(app.config.get("MIGRATION_BACKUP_DIR") or DATA_ROOT / "backups")
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / f"pre-user-migration-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
                with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(str(backup_file))) as snapshot:
                    source.backup(snapshot)
                    if snapshot.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError("User migration backup failed validation; accounts were not changed.")
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE user ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT 0"))
        seed_database()
        if db.engine.dialect.name == 'sqlite':
            # Migrations above use their own transaction strategy. Enforce links
            # for request connections only after validating the existing data.
            with db.engine.connect() as connection:
                if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
                    raise RuntimeError('Database has broken record links; restore a verified backup before starting.')
                connection.exec_driver_sql('PRAGMA user_version=1')
            @event.listens_for(db.engine, 'connect')
            def sqlite_foreign_keys(connection, _record):
                connection.execute('PRAGMA foreign_keys=ON')
            db.session.remove()
            if db.engine.url.database != ':memory:':
                db.engine.dispose()

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
    user = db.session.get(User, uid) if uid else None
    if user and not user.deleted:
        stamp = session.get('auth_stamp')
        if not stamp or not secrets.compare_digest(stamp, hashlib.sha256(user.password_hash.encode()).hexdigest()):
            return None
        return user
    return None


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


def report_period_from_request():
    args = request.args
    if 'from_month' not in args and 'from_year' not in args:
        return period_from_request()
    try:
        first, end = month_period({'year': args.get('from_year'), 'month_number': args.get('from_month')})
        if args.get('period_mode') != 'one' and (args.get('to_year') or args.get('to_month')):
            last, end = month_period({'year': args.get('to_year'), 'month_number': args.get('to_month')})
            if last < first:
                first, end = last, month_period({'year': first.year, 'month_number': first.month})[1]
        return first, end
    except ValueError as exc:
        abort(400, description=str(exc))


def parse_money(value):
    try:
        cleaned = str(value or "0").replace(",", "").strip()
        amount = Decimal(cleaned)
        if not amount.is_finite() or abs(amount) >= Decimal('1000000000000'):
            raise ValueError
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if abs(amount) >= Decimal('1000000000000'):
            raise ValueError
        return amount
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError("Enter a valid amount.")


def month_period(values):
    try:
        start = date(int(values.get('year', '')), int(values.get('month_number', '')), 1)
        if not 1900 <= start.year <= 9998:
            raise ValueError()
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        return start, end
    except (TypeError, ValueError, OverflowError):
        raise ValueError('Select a valid month and year.')


def live_transactions():
    deleted = select(AuditLog.entity_id).where(AuditLog.entity_type == 'transaction', AuditLog.action == 'delete')
    return Transaction.query.filter(~func.cast(Transaction.id, db.String).in_(deleted))


def group_codes():
    codes = {g.id: numeric_part(g.id) // 10 for g in Group.query.all()}
    for record in AuditLog.query.filter_by(entity_type='group', action='group_code').order_by(AuditLog.id).all():
        codes[record.entity_id] = int(record.details)
    return codes


def particular_codes():
    codes = {c.id: numeric_part(c.id) * 10 for c in Category.query.all()}
    for record in AuditLog.query.filter_by(entity_type='category', action='account_code').order_by(AuditLog.id).all():
        codes[record.entity_id] = int(record.details)
    return codes


def set_account_code(item, raw):
    is_group = isinstance(item, Group)
    prefix = (GROUP_PREFIX if is_group else CATEGORY_PREFIX)[item.kind] + '_'
    raw = raw.strip().upper()
    if raw.startswith(prefix):
        raw = raw[len(prefix):]
    if not raw.isdigit() or not 1 <= int(raw) < 900000:
        raise ValueError('Enter a numeric code or a code with the correct account prefix.')
    model = Group if is_group else Category
    codes = group_codes() if is_group else particular_codes()
    if any(other.id != item.id and codes[other.id] == int(raw) for other in model.query.filter_by(kind=item.kind).all()):
        raise ValueError('That code is already used for this account type.')
    audit('group_code' if is_group else 'account_code', 'group' if is_group else 'category', item.id, str(int(raw)))


def next_public_code(model, kind, exclude_id, step):
    codes = group_codes() if model is Group else particular_codes()
    values = [codes[item.id] for item in model.query.filter_by(kind=kind).all()
              if item.id != exclude_id and codes[item.id] < 900000]
    candidate = max([0] + values) + step
    if candidate >= 900000:
        raise ValueError('No automatic code available. Choose an unused code below 900000.')
    return str(candidate)


def sorted_groups(items):
    codes = group_codes()
    return sorted(items, key=lambda g: (g.kind != 'income', codes.get(g.id, 0), g.id))


def sorted_categories(items):
    codes = group_codes()
    particulars = particular_codes()
    return sorted(items, key=lambda c: (c.kind != 'income', codes.get(c.group_id, 0), particulars[c.id], c.id))


def account_catalog_plan(retire_unused=False):
    """Plan a non-destructive chart update against the current database."""
    groups = Group.query.all()
    particulars = Category.query.all()
    current_group_codes = group_codes()
    current_particular_codes = particular_codes()
    posted_ids = {row[0] for row in db.session.query(Transaction.category_id).distinct()}
    matched_groups, matched_particulars = set(), set()
    desired_groups, desired_particulars, changes, blocked = [], [], [], []

    def find_match(items, kind, name, used, desired_code, codes):
        labels = {name.casefold(), *(alias.casefold() for alias in CATALOG_ALIASES.get((kind, name), ()))}
        candidates = [item for item in items if item.kind == kind and item.name.strip().casefold() in labels
                      and item.id not in used]
        if len(candidates) > 1:
            # A posted account must keep its internal ID so historical entries
            # follow the new code. If neither copy is posted, retain the copy
            # already carrying the requested code. Never guess between two
            # posted copies or two equally plausible unused copies.
            posted = [item for item in candidates if isinstance(item, Category) and item.id in posted_ids]
            if len(posted) == 1:
                return posted[0]
            if not posted:
                active = [item for item in candidates if item.active]
                if len(active) == 1:
                    return active[0]
                exact_code = [item for item in candidates if codes[item.id] == int(desired_code.split('_')[1])]
                if len(exact_code) == 1:
                    return exact_code[0]
            blocked.append(f'Ambiguous match for {kind} / {name}. Review duplicate names first.')
            return None
        return candidates[0] if candidates else None

    for kind, code, name in CATALOG_GROUPS:
        item = find_match(groups, kind, name, matched_groups, code, current_group_codes)
        if item:
            matched_groups.add(item.id)
            before = format_id(GROUP_PREFIX[kind], current_group_codes[item.id], 4)
            if before != code or item.name != name or not item.active:
                changes.append(f'Group: {before} · {item.name} → {code} · {name}')
        else:
            changes.append(f'Add group: {code} · {name}')
        desired_groups.append((kind, code, name, item))

    for kind, group_code, code, name in CATALOG_PARTICULARS:
        item = find_match(particulars, kind, name, matched_particulars, code, current_particular_codes)
        if item:
            matched_particulars.add(item.id)
            before = format_id(CATEGORY_PREFIX[kind], current_particular_codes[item.id], 4)
            group_name = next(gname for gkind, gcode, gname, _ in desired_groups if gcode == group_code)
            if before != code or item.name != name or item.group_name != group_name or not item.active:
                changes.append(f'Particular: {before} · {item.name} → {code} · {name} ({group_name})')
        else:
            changes.append(f'Add particular: {code} · {name}')
        desired_particulars.append((kind, group_code, code, name, item))

    unmatched_particulars = [item for item in particulars if item.id not in matched_particulars]
    legacy_particulars = [item for item in unmatched_particulars if retire_unused
                          if item.active or current_particular_codes[item.id] < 900000]
    for item in unmatched_particulars:
        if retire_unused and item.id in posted_ids:
            blocked.append(f'Posted account needs manual mapping: {item.id} · {item.name}')
        elif item in legacy_particulars:
            changes.append(f'Hide unused old particular: {item.name}')
    legacy_groups = [item for item in groups if retire_unused and item.id not in matched_groups
                     and not any(c.group_id == item.id and c.id in matched_particulars for c in particulars)
                     and (item.active or current_group_codes[item.id] < 900000)]
    for item in legacy_groups:
        changes.append(f'Hide old group: {item.name}')

    # Custom accounts are retained by default. Never silently steal their codes.
    for desired, existing, matched, retired, codes in (
        ([(k, c) for k, c, _, _ in desired_groups], groups, matched_groups, legacy_groups, current_group_codes),
        ([(k, c) for k, _, c, _, _ in desired_particulars], particulars, matched_particulars, legacy_particulars, current_particular_codes),
    ):
        wanted = {(kind, int(code.split('_')[1])) for kind, code in desired}
        retired_ids = {item.id for item in retired}
        for item in existing:
            if item.id not in matched and item.id not in retired_ids and (item.kind, codes[item.id]) in wanted:
                blocked.append(f'Code conflict with retained account: {item.name}. Edit its code or explicitly review retiring unused legacy accounts.')

    snapshot = {
        'retire_unused': retire_unused,
        'groups': sorted((g.id, g.kind, g.name, g.active, current_group_codes[g.id]) for g in groups),
        'particulars': sorted((c.id, c.kind, c.group_id, c.name, c.active,
                               current_particular_codes[c.id]) for c in particulars),
        'posted': sorted(posted_ids),
        'audit_id': db.session.query(func.max(AuditLog.id)).scalar(),
    }
    fingerprint = hashlib.sha256(json.dumps(snapshot, default=str).encode()).hexdigest()
    return {'groups': desired_groups, 'particulars': desired_particulars,
            'retire_unused': retire_unused,
            'legacy_groups': legacy_groups, 'legacy_particulars': legacy_particulars,
            'changes': changes, 'blocked': blocked, 'fingerprint': fingerprint}


def apply_account_catalog(plan):
    """Apply an already-validated plan in one database transaction."""
    groups_by_code = {}
    for kind, code, name, item in plan['groups']:
        if item is None:
            item = Group(kind=kind, name=name)
            db.session.add(item)
            db.session.flush()
        item.name, item.active = name, True
        groups_by_code[code] = item
        audit('group_code', 'group', item.id, str(int(code.split('_')[1])))
    for kind, group_code, code, name, item in plan['particulars']:
        group = groups_by_code[group_code]
        if item is None:
            item = Category(kind=kind, group_id=group.id, group_name=group.name, name=name)
            db.session.add(item)
            db.session.flush()
        item.group_id, item.group_name, item.name, item.active = group.id, group.name, name, True
        audit('account_code', 'category', item.id, str(int(code.split('_')[1])))
    # Unused legacy accounts remain in audit/history but cannot be chosen for
    # new entries. Their reserved codes cannot collide with workbook codes.
    reserved_group = max([900000] + list(group_codes().values()))
    reserved_particular = max([900000] + list(particular_codes().values()))
    for index, item in enumerate(plan['legacy_groups'], 1):
        item.active = False
        audit('group_code', 'group', item.id, str(reserved_group + index))
    for index, item in enumerate(plan['legacy_particulars'], 1):
        item.active = False
        audit('account_code', 'category', item.id, str(reserved_particular + index))
    audit('catalog_sync', 'database', None,
          f"Account chart: {len(plan['groups'])} groups, {len(plan['particulars'])} particulars")
    db.session.flush()


def period_from_request():
    if 'month_number' in request.args or 'year' in request.args:
        try:
            return month_period(request.args)
        except ValueError as exc:
            abort(400, description=str(exc))
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
        live_transactions().join(Category)
        .options(selectinload(Transaction.category), selectinload(Transaction.adjustments))
        .filter(Transaction.cash_date.between(start, end))
        .order_by(Transaction.cash_date, Transaction.id)
        .all()
    )


def report_groups():
    # Include historical category groups even when disabled for new entries.
    keys = {(g.kind, g.name) for g in Group.query.all()}
    keys.update((c.kind, c.group_name) for c in Category.query.all())
    ranks = {(g.kind, g.name): n for n, g in enumerate(sorted_groups(Group.query.all()))}
    codes = group_codes()
    labels = {(g.kind, g.name): format_id(GROUP_PREFIX[g.kind], codes[g.id], 4) for g in Group.query.all()}
    return [{"kind": kind, "name": name, "code": labels.get((kind, name), ''), "key": json.dumps([kind, name])}
            for kind, name in sorted(keys, key=lambda k: (k[0] != "income", ranks.get(k, 999999), k[1]))]


def selected_report_groups():
    options = report_groups()
    selected = list(dict.fromkeys(request.args.getlist("group")))
    if set(selected) - {g["key"] for g in options}:
        abort(400, description="Unknown report group. Select groups from the report form.")
    return options, selected


def build_report(start, end, report_type="monthly", selected_groups=None):
    if live_transactions().filter(Transaction.cash_date.between(start, end)).limit(25001).count() > 25000:
        abort(400, 'This report exceeds 25,000 entries. Select a shorter period.')
    codes = particular_codes()
    group_order = {(g['kind'], g['name']): rank for rank, g in enumerate(report_groups())}
    selected = {tuple(json.loads(key)) for key in (selected_groups or [])}

    def includes(c):
        if selected and (c.kind, c.group_name) not in selected:
            return False
        if report_type == "direct" and not c.service_line:
            return False
        if report_type == "rental" and not c.entity_name:
            return False
        if report_type == "construction" and "Construction" not in c.group_name:
            return False
        return True

    txns = base_transactions(start, end)
    filtered = []
    for txn in txns:
        c = txn.category
        if not includes(c):
            continue
        filtered.append(txn)

    rows = []
    for txn in filtered:
        c = txn.category
        adjusted = txn.adjusted_total
        rows.append({
            "Category ID": c.id,
            "Date": txn.cash_date.isoformat(),
            "Reference": txn.reference,
            "Type": c.kind.title(),
            "Group": c.group_name,
            "Account Code": format_id(CATEGORY_PREFIX[c.kind], codes[c.id], 4),
            "Particular": c.name,
            "Service / Property": c.service_line or c.entity_name or "—",
            "Counterparty": txn.counterparty,
            "Subtotal": txn.subtotal,
            "SSCL": txn.sscl,
            "VAT": txn.vat,
            "Original Total": txn.total,
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
        grouped.setdefault(key, {"income": Decimal('0.00'), "expense": Decimal('0.00')})
        grouped[key][row["Type"].lower()] += row["Cash Total"]
    summary_order = {}
    for row in rows:
        label = row['Service / Property'] if report_type in {'direct', 'rental'} else row['Group']
        rank = group_order.get((row['Type'].lower(), row['Group']), 999999)
        summary_order[label] = min(summary_order.get(label, rank), rank)
    summary = [
        {"label": key, **values, "pl": values["income"] - values["expense"]}
        for key, values in sorted(grouped.items(), key=lambda item: (summary_order[item[0]], item[0]))
    ]
    columns = ["Subtotal", "SSCL", "VAT", "Adjustments", "Cash Total"]
    account_totals = {}
    for row in rows:
        totals = account_totals.setdefault(row["Category ID"], dict.fromkeys(columns, Decimal('0.00')))
        for col in columns:
            totals[col] += row[col]
    sections = []
    for kind in ("income", "expense"):
        groups = {}
        for c in sorted_categories(Category.query.filter_by(kind=kind).all()):
            if not includes(c) or c.id not in account_totals:
                continue
            group = groups.setdefault(c.group_name, {"name": c.group_name, "items": [], "totals": dict.fromkeys(columns, Decimal('0.00'))})
            amounts = account_totals.get(c.id, dict.fromkeys(columns, Decimal('0.00')))
            group["items"].append({"code": format_id(CATEGORY_PREFIX[c.kind], codes[c.id], 4), "name": c.name, "amounts": amounts})
            for col in columns:
                group["totals"][col] += amounts[col]
        sections.append({"kind": kind, "label": "Income" if kind == "income" else "Expenditure",
                         "groups": sorted(groups.values(), key=lambda g: (group_order.get((kind, g['name']), 999999), g['name'])),
                         "totals": {col: sum(g["totals"][col] for g in groups.values()) for col in columns}})
    return {"rows": rows, "summary": summary, "sections": sections, "columns": columns,
            "income": income, "expense": expense, "pl": income - expense}


def export_report_xlsx(start, end, report_type, selected_groups=None):
    data = build_report(start, end, report_type, selected_groups)
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
    with closing(Workbook()) as workbook:
        workbook.remove(workbook.active)
        def write_rows(name, rows):
            sheet = workbook.create_sheet(name)
            headers = list(dict.fromkeys(key for row in rows for key in row))
            for col, header in enumerate(headers, 1):
                sheet.cell(5, col, header)
            for row_index, row in enumerate(rows, 6):
                for col, header in enumerate(headers, 1):
                    value = row.get(header)
                    if isinstance(value, str):
                        value = ILLEGAL_CHARACTERS_RE.sub('', value)
                    sheet.cell(row_index, col, value)
        grouped_rows = []
        styled_rows = []
        section_rows = []
        total_rows = []
        def statement_row(label, amounts=None, code="", bold=False, number="", style=None):
            if style == 'section':
                section_rows.append(len(grouped_rows) + 6)
            elif style == 'total':
                total_rows.append(len(grouped_rows) + 6)
            if bold:
                styled_rows.append(len(grouped_rows) + 6)
            if report_type == "short":
                grouped_rows.append({"Group": label, "Cash Total": amounts["Cash Total"] if amounts else None})
            else:
                amount = amounts["Cash Total"] if amounts else None
                grouped_rows.append({"No.": number, "Particular": label, "A/C code": code,
                                     "Amount (LKR)": amount if not bold else None,
                                     "Total (LKR)": amount if bold else None})
        for section in data["sections"]:
            if not section["groups"]:
                continue
            statement_row(section["label"] + " Particulars", bold=True, style='section')
            for group in section["groups"]:
                if report_type == "short":
                    statement_row(group["name"], group["totals"], bold=True)
                else:
                    statement_row(group["name"], bold=True)
                    for number, item in enumerate(group["items"], start=1):
                        statement_row(item["name"], item["amounts"], item["code"], number=number)
                    statement_row(group["name"] + " — Total", group["totals"], bold=True)
            statement_row("Total " + section["label"], section["totals"], bold=True, style='total')
        statement_row("Liquid P/L", {col: data["pl"] if col == "Cash Total" else None for col in data["columns"]}, bold=True, style='total')
        write_rows("Group Report", grouped_rows)
        write_rows("Summary", summary_rows)
        if report_type != "short":
            write_rows("Detailed Ledger", [{k: v for k, v in row.items() if k != "Category ID"} for row in data["rows"]])
        for ws in workbook.worksheets:
            ws["A1"] = "K.Y.S. Cash-Based P&L Management System"
            ws["A2"] = title_map.get(report_type, title_map["monthly"])
            ws["A3"] = f"Cash period: {start:%d %b %Y} to {end:%d %b %Y}"
            ws["A4"] = "Groups: " + (", ".join(f"{json.loads(key)[0].title()}: {json.loads(key)[1]}" for key in selected_groups) if selected_groups else "All groups")
            ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
            ws["A1"].fill = PatternFill("solid", fgColor="0D3B34")
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(ws.max_column, 2 if report_type == "short" else 4))
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
                    if isinstance(cell.value, (int, float, Decimal)):
                        cell.number_format = '#,##0.00;[Red]-#,##0.00'
                    elif cell.data_type == "f":
                        cell.data_type = "s"
        ws = workbook["Group Report"]
        ws.auto_filter.ref = None
        widths = {'A': 58, 'B': 22} if report_type == 'short' else {'A': 6, 'B': 60, 'C': 15, 'D': 20, 'E': 20}
        for letter, width in widths.items():
            ws.column_dimensions[letter].width = width
        ws.row_dimensions[5].height = 22
        for row in ws.iter_rows(min_row=6):
            lines = 1
            for cell in row:
                cell.font = Font(name='Calibri', size=11, color='29363E')
                cell.alignment = Alignment(vertical="center", wrap_text=True,
                                           horizontal="right" if isinstance(cell.value, (int, float, Decimal)) else "left")
                cell.border = Border(bottom=Side(style="thin", color="D6E0DC"))
                if isinstance(cell.value, str):
                    capacity = max(1, int(ws.column_dimensions[cell.column_letter].width - 3))
                    lines = max(lines, (len(cell.value) + capacity - 1) // capacity)
            if report_type != "short":
                row[0].number_format = '0'
            ws.row_dimensions[row[0].row].height = 20 if lines == 1 else 15 * lines + 5
        for row_number in styled_rows:
            for cell in ws[row_number]:
                cell.font = Font(name='Calibri', size=11, bold=True, color="29363E")
                cell.fill = PatternFill("solid", fgColor="E8EDEE")
        for row_number in section_rows:
            ws.row_dimensions[row_number].height = 26
            for cell in ws[row_number]:
                cell.font = Font(name='Calibri', size=13, bold=True, color='FFFFFF')
                cell.fill = PatternFill('solid', fgColor='4B6575')
        for row_number in total_rows:
            ws.row_dimensions[row_number].height = max(ws.row_dimensions[row_number].height, 23)
            for cell in ws[row_number]:
                cell.border = Border(top=Side(style='thin', color='4B6575'), bottom=Side(style='double', color='4B6575'))
                cell.fill = PatternFill('solid', fgColor='F1F0EC')
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.print_title_rows = "1:5"
        ws.print_area = f"A1:{'B' if report_type == 'short' else 'E'}{ws.max_row}"
        ws.cell(ws.max_row + 2, 1, "Total Liquid Income − Total Expenditure = Liquid P/L")
        ws.cell(ws.max_row + 1, 1, f"{data['income']:,.2f} − {data['expense']:,.2f} = {data['pl']:,.2f} LKR")
        ws.print_area = f"A1:E{ws.max_row}"
        if report_type == "short":
            ws.column_dimensions["A"].width = 58
            ws.column_dimensions["B"].width = 22
            ws.print_area = f"A1:B{ws.max_row}"
        ws.print_options.horizontalCentered = True
        workbook.save(output)
    output.seek(0)
    return output


def remembered_entry_period():
    user = current_user()
    if user:
        record = AuditLog.query.filter_by(action='entry_period', entity_type='user',
            entity_id=str(user.id)).order_by(AuditLog.id.desc()).first()
        if record:
            saved = parse_date(record.details)
            if saved:
                return saved.replace(day=1)
    return parse_date(session.get('entry_month'), date.today().replace(day=1))


def remember_entry_period(period):
    record = AuditLog.query.filter_by(action='entry_period', entity_type='user',
        entity_id=str(current_user().id)).order_by(AuditLog.id.desc()).first()
    if not record or record.details != period.isoformat():
        audit('entry_period', 'user', current_user().id, period.isoformat())
    session['entry_month'] = period.isoformat()


def register_context(app):
    @app.context_processor
    def shared():
        gc, pc = group_codes(), particular_codes()
        return {
            "current_user": current_user(), "TASKS": TASKS, "ROLES": ROLES,
            "app_version": VERSION,
            "backup_status": read_status(DATA_ROOT) if current_user() and current_user().role == 'admin' else {},
            "today": date.today(), "csrf_token": session.get("csrf_token", ""),
            "entry_period": remembered_entry_period(),
            "live_revision": getattr(g, "live_revision", None),
            "group_codes": gc,
            "group_labels": {g.id: format_id(GROUP_PREFIX[g.kind], gc[g.id], 4) for g in Group.query.all()},
            "particular_labels": {c.id: format_id(CATEGORY_PREFIX[c.kind], pc[c.id], 4) for c in Category.query.all()},
        }

    @app.template_filter("money")
    def money(value):
        return f"{value or 0:,.2f}"

    @app.before_request
    def csrf_and_session():
        if request.endpoint in {"dashboard", "transactions", "reports"}:
            g.live_revision = data_revision()
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        if request.method == "POST":
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not secrets.compare_digest(token or "", session.get("csrf_token", "")):
                abort(400, "Invalid or expired form token. Refresh the page and try again.")
            financial = {'transaction_new', 'transaction_edit', 'transaction_delete',
                         'transaction_delete_selected', 'adjustment_new'}
            if request.endpoint in financial and current_user() and current_user().active:
                # Serialize financial writes so concurrent edits and deletions cannot race.
                if db.engine.dialect.name == 'sqlite':
                    db.session.execute(text('BEGIN IMMEDIATE'))


def data_revision():
    latest = AuditLog.query.filter(AuditLog.action.notin_(
        ['login', 'logout', 'export', 'backup', 'entry_period']
    )).order_by(AuditLog.id.desc()).first()
    value = f'{latest.id}:{latest.happened_at}' if latest else 'empty'
    return hashlib.sha256(value.encode()).hexdigest()


def register_routes(app):
    login_attempts = {}
    login_lock = threading.Lock()
    @app.errorhandler(OperationalError)
    def database_unavailable(error):
        db.session.rollback()
        app.logger.exception('Database operation failed')
        return render_template('error.html', code=503, message='Database is busy or unavailable. Check the ledger before retrying a save.'), 503

    @app.errorhandler(IntegrityError)
    def database_conflict(error):
        db.session.rollback()
        return render_template('error.html', code=409, message='This change conflicts with another record. Refresh and review before retrying.'), 409
    @app.get('/updates/version')
    def updates_version():
        user = current_user()
        if not user or not user.active:
            return {'error': 'Sign in required'}, 401, {'Cache-Control': 'no-store'}
        version = data_revision()
        if request.if_none_match.contains(version):
            response = app.response_class(status=304)
        else:
            response = app.json.response({'version': version})
        response.set_etag(version)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get("/health")
    def health():
        db.session.execute(text('SELECT 1'))
        return {"status": "ok", "database": "connected", "service": "kys-finance", "version": VERSION}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            key = request.remote_addr or 'unknown'
            now = time.monotonic()
            with login_lock:
                expired = [address for address, attempts in login_attempts.items() if not attempts or attempts[-1] < now - 300]
                for address in expired:
                    del login_attempts[address]
                if len(login_attempts) >= 10000 and key not in login_attempts:
                    abort(429, 'Too many login attempts. Try again later.')
                attempts = login_attempts.setdefault(key, deque())
                while attempts and attempts[0] < now - 300:
                    attempts.popleft()
                if len(attempts) >= 10:
                    abort(429, 'Too many login attempts. Wait five minutes before trying again.')
                attempts.append(now)
            user = User.query.filter(func.lower(User.username) == username.lower()).first()
            if user and user.active and not user.deleted and check_password_hash(user.password_hash, request.form.get("password", "")):
                with login_lock:
                    login_attempts.pop(key, None)
                session.clear()
                session["user_id"] = user.id
                session['auth_stamp'] = hashlib.sha256(user.password_hash.encode()).hexdigest()
                session["csrf_token"] = secrets.token_urlsafe(24)
                audit("login", "user", user.id, "Successful sign in")
                db.session.commit()
                destination = request.args.get('next', '')
                if not destination.startswith('/') or destination.startswith('//') or '\\' in destination:
                    destination = url_for('dashboard')
                return redirect(destination)
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
        if not current_user().can('view_reports'):
            if current_user().can('delete_entries') or current_user().can('edit_entries'):
                return redirect(url_for('transactions'))
            if current_user().can('income_entry'):
                return redirect(url_for('transaction_new', kind='income'))
            if current_user().can('expense_entry'):
                return redirect(url_for('transaction_new', kind='expense'))
            abort(403)
        today = date.today()
        start = today.replace(day=1)
        selected = request.args.get("month", "")
        if 'month_number' in request.args:
            try:
                selected = month_period(request.args)[0].strftime('%Y-%m')
            except ValueError as exc:
                abort(400, description=str(exc))
        if selected:
            try:
                start = date.fromisoformat(selected + "-01")
                if start.strftime("%Y-%m") != selected:
                    raise ValueError("Invalid month")
            except ValueError:
                abort(400)
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        data = build_report(start, end, "monthly")
        recent = live_transactions().filter(Transaction.cash_date.between(start, end)).order_by(
            Transaction.cash_date.desc(), Transaction.id.desc()).limit(20).all()
        monthly = []
        for offset in range(5, -1, -1):
            month_index = today.year * 12 + today.month - 1 - offset
            year, month_number = divmod(month_index, 12)
            month = date(year, month_number + 1, 1)
            nxt = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = nxt - timedelta(days=1)
            report = build_report(month, month_end, "monthly")
            monthly.append({**report, "label": month.strftime("%b"),
                            "full_label": month.strftime("%B %Y"), "start": month, "end": month_end})
        return render_template("dashboard.html", data=data, recent=recent, monthly=monthly,
                               selected_start=start, selected_end=end,
                               selected_label=start.strftime("%B %Y"))

    @app.get("/transactions")
    @login_required
    def transactions():
        start, end = period_from_request()
        kind = request.args.get("kind", "")
        query = live_transactions().join(Category).filter(Transaction.cash_date.between(start, end))
        if not (current_user().can('view_reports') or current_user().can('delete_entries') or current_user().can('edit_entries')):
            query = query.filter(Transaction.created_by_id == current_user().id)
        if kind in {"income", "expense"}:
            query = query.filter(Category.kind == kind)
        page = max(1, request.args.get('page', 1, type=int))
        paged = query.options(selectinload(Transaction.category), selectinload(Transaction.adjustments), selectinload(Transaction.created_by)).order_by(Transaction.cash_date.desc(), Transaction.id.desc()).paginate(page=page, per_page=100, error_out=False)
        return render_template("transactions.html", items=paged.items, pagination=paged, start=start, end=end, kind=kind)

    @app.post('/account/entry-period')
    @login_required
    def entry_period_save():
        user = current_user()
        if not (user.can('income_entry') or user.can('expense_entry')):
            abort(403)
        try:
            period, _ = month_period(request.form)
        except ValueError as exc:
            return {'error': str(exc)}, 400
        remember_entry_period(period)
        db.session.commit()
        return {'month': period.isoformat()}

    @app.route("/transactions/new", methods=["GET", "POST"])
    @login_required
    def transaction_new():
        requested_kind = request.args.get("kind", request.form.get("kind", "income"))
        if requested_kind not in {"income", "expense"}:
            requested_kind = "income"
        task = "income_entry" if requested_kind == "income" else "expense_entry"
        if not current_user().can(task):
            abort(403)
        categories = sorted_categories(Category.query.join(Group, Category.group_id == Group.id).filter(
            Category.kind == requested_kind, Category.active.is_(True), Group.active.is_(True)).all())
        if request.method == "POST":
            try:
                category = db.session.get(Category, request.form.get("category_id", "").strip())
                submission = request.form.get('submission_token', '')
                if len(submission) != 32 or any(c not in '0123456789abcdef' for c in submission):
                    abort(400, 'Refresh the entry form before saving.')
                payload = {key: request.form.getlist(key) for key in sorted(request.form)
                           if key not in {'csrf_token', 'submission_token'}}
                payload['requested_kind'] = requested_kind
                digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                saved = AuditLog.query.filter_by(action='entry_submission', entity_type='submission',
                                                entity_id=submission).first()
                if saved:
                    previous = json.loads(saved.details)
                    if saved.user_id != current_user().id or previous['digest'] != digest:
                        abort(409, 'This save token was already used. Open a new entry form.')
                    flash('This entry was already saved. No duplicate was added.', 'success')
                    return redirect(url_for('transaction_new', kind=requested_kind))
                selected_group = request.form.get("group_name", "").strip()
                if not selected_group:
                    raise ValueError("Select a group.")
                if not category or category.kind != requested_kind or not category.active or category.group_name != selected_group:
                    raise ValueError("Select a valid account.")
                group = db.session.get(Group, category.group_id)
                if not group or not group.active:
                    raise ValueError('This group is disabled. Select an active group.')
                cash_date = month_period(request.form)[0] if 'month_number' in request.form else parse_date(request.form.get("cash_date"))
                if not cash_date:
                    raise ValueError("Select the actual cash date.")
                subtotal = parse_money(request.form.get("subtotal"))
                sscl = parse_money(request.form.get("sscl"))
                vat = parse_money(request.form.get("vat"))
                if sscl or vat:
                    raise ValueError("Enter SSCL and VAT as separate tax particulars, not in these amount fields.")
                if min(subtotal, sscl, vat) < 0:
                    raise ValueError("Amounts cannot be negative.")
                total = round(subtotal + sscl + vat, 2)
                if total <= 0:
                    raise ValueError("Grand total must be greater than zero.")
                reference = request.form.get("reference", "").strip()
                counterparty = request.form.get("counterparty", "").strip()
                item = Transaction(
                    cash_date=cash_date, category_id=category.id,
                    reference=reference, counterparty=counterparty,
                    description=request.form.get("description", "").strip(), subtotal=subtotal,
                    sscl=sscl, vat=vat, total=total, created_by_id=current_user().id,
                )
                db.session.add(item)
                db.session.flush()
                audit("create", "transaction", item.id, f"{requested_kind} {total:.2f} / {reference}")
                audit('entry_submission', 'submission', submission,
                      json.dumps({'digest': digest, 'transaction_id': item.id}))
                remember_entry_period(cash_date.replace(day=1))
                db.session.commit()
                flash(f"Cash {requested_kind} saved. The ledger entry is now locked.", "success")
                return redirect(url_for("transaction_new", kind=requested_kind))
            except (ValueError, TypeError) as exc:
                db.session.rollback()
                flash(str(exc), "error")
        subtotal_only_groups = {name for kind, name in SUBTOTAL_ONLY_GROUPS if kind == requested_kind}
        subtotal_only_groups.update(c.group_name for c in categories if c.service_line or c.name in {'SSCL', 'VAT'})
        if requested_kind == 'expense':
            subtotal_only_groups.update(c.group_name for c in categories)
        return render_template("transaction_form.html", kind=requested_kind, categories=categories,
                               submission_token=request.form.get('submission_token') or secrets.token_hex(16),
                               subtotal_only_groups=subtotal_only_groups)

    @app.route('/transactions/<int:transaction_id>/delete', methods=['GET', 'POST'])
    @task_required('delete_entries')
    def transaction_delete(transaction_id):
        txn = live_transactions().filter_by(id=transaction_id).first_or_404()
        if request.method == 'POST':
            if request.form.get('confirmed') != 'yes':
                flash('Please confirm before deleting this entry.', 'error')
            else:
                audit('delete', 'transaction', txn.id, json.dumps({'confirmation': 'Confirmed by signed-in user', 'reference': txn.reference,
                    'date': txn.cash_date.isoformat(), 'total': str(txn.total),
                    'deleted_cash_total': str(txn.adjusted_total), 'account': txn.category_id}))
                db.session.commit()
                flash('Entry deleted from totals and reports. Its audit record is retained.', 'success')
                return redirect(url_for('transactions', year=txn.cash_date.year, month_number=txn.cash_date.month))
        return render_template('transaction_delete.html', txn=txn)

    @app.post('/transactions/delete-selected')
    @task_required('delete_entries')
    def transaction_delete_selected():
        raw_ids = request.form.getlist('transaction_ids')
        if not raw_ids or len(raw_ids) > 100 or len(set(raw_ids)) != len(raw_ids) or any(
                not value.isdecimal() or int(value) <= 0 for value in raw_ids):
            abort(400, 'Select between 1 and 100 distinct ledger entries.')
        if request.form.get('confirmed') != 'yes':
            abort(400, 'Confirm deletion of the selected entries.')
        ids = [int(value) for value in raw_ids]
        transactions = live_transactions().filter(Transaction.id.in_(ids)).all()
        if len(transactions) != len(ids):
            abort(409, 'One or more selected entries have changed. Refresh the ledger and try again.')
        for txn in transactions:
            audit('delete', 'transaction', txn.id, json.dumps({
                'confirmation': 'Confirmed selected-entry deletion by signed-in user',
                'reference': txn.reference, 'date': txn.cash_date.isoformat(),
                'total': str(txn.total), 'deleted_cash_total': str(txn.adjusted_total),
                'account': txn.category_id}))
        db.session.commit()
        flash(f'{len(transactions)} selected entries removed from totals and reports. Audit records are retained.', 'success')
        return redirect(url_for('transactions', year=transactions[0].cash_date.year,
                                month_number=transactions[0].cash_date.month))

    @app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
    @task_required('edit_entries')
    def transaction_edit(transaction_id):
        # Financial POSTs are serialized in csrf_and_session before period checks.
        txn = live_transactions().filter_by(id=transaction_id).first_or_404()
        current_total = txn.total + sum((item.amount for item in txn.adjustments), Decimal('0'))
        version = str(max((item.id for item in txn.adjustments), default=0))
        if request.method == "POST":
            try:
                if request.form.get('version') != version:
                    raise ValueError('This entry changed since you opened it. Review the current amount and try again.')
                raw_total = request.form.get('total', '').strip()
                if not raw_total:
                    raise ValueError('Enter the correct total amount.')
                new_total = Decimal(str(parse_money(raw_total)))
                reason = request.form.get('reason', '').strip()
                if new_total <= 0:
                    raise ValueError('The total must be greater than zero. Use Delete entry to remove an incorrect entry.')
                if not reason or len(reason) > 240:
                    raise ValueError('Enter a reason (up to 240 characters).')
                difference = new_total - current_total
                if difference:
                    db.session.add(Adjustment(transaction_id=txn.id, effective_date=date.today(),
                        amount=difference, reason=reason, created_by_id=current_user().id))
                    audit('edit', 'transaction', txn.id, json.dumps({
                        'previous_total': str(current_total), 'new_total': str(new_total), 'reason': reason}))
                    db.session.commit()
                    flash('Entry updated. The previous amount is retained in audit history.', 'success')
                else:
                    db.session.rollback()
                    flash('No change: this entry already has that total.', 'info')
                return redirect(url_for('transactions', year=txn.cash_date.year, month_number=txn.cash_date.month))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), 'error')
        return render_template('transaction_edit.html', txn=txn, current_total=current_total, version=version)

    @app.route("/transactions/<int:transaction_id>/adjust", methods=["GET", "POST"])
    @role_required("admin")
    def adjustment_new(transaction_id):
        txn = live_transactions().filter_by(id=transaction_id).first_or_404()
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
        start, end = report_period_from_request()
        report_type = request.args.get("type", "monthly")
        if report_type not in {"monthly", "short"}:
            report_type = "monthly"
        groups, selected_groups = selected_report_groups()
        data = build_report(start, end, report_type, selected_groups)
        return render_template("reports.html", data=data, start=start, end=end, report_type=report_type,
                               groups=groups, selected_groups=selected_groups)

    @app.get("/reports/export")
    @task_required("view_reports")
    def reports_export():
        start, end = report_period_from_request()
        report_type = request.args.get("type", "monthly")
        if report_type not in {"monthly", "short"}:
            report_type = "monthly"
        groups, selected_groups = selected_report_groups()
        output = export_report_xlsx(start, end, report_type, selected_groups)
        audit("export", "report", None, f"{report_type}: {start} to {end}; groups: {selected_groups or 'All'}")
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
        return render_template("users.html", users=User.query.filter_by(deleted=False).order_by(User.active.desc(), User.display_name).all())

    @app.route("/users/new", methods=["GET", "POST"])
    @role_required("admin")
    def user_new():
        if request.method == "POST":
            try:
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "")
                role = request.form.get("role", "data_entry")
                if not username or len(password) < 6 or role not in ROLES:
                    raise ValueError("Use a username, valid role, and password of at least 6 characters.")
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
        if user.deleted:
            abort(404)
        if request.method == "POST":
            username = request.form.get("username", user.username).strip()
            role = request.form.get("role", "data_entry")
            password = request.form.get("password", "")
            active = request.form.get("active", "yes" if user.active else "no") == "yes"
            try:
                if not username or role not in ROLES:
                    raise ValueError("Enter a username and select a valid role.")
                if password and len(password) < 6:
                    raise ValueError("A reset password must be at least 6 characters.")
                existing = User.query.filter(func.lower(User.username) == username.lower(), User.id != user.id).first()
                if existing:
                    raise ValueError("That username is already in use, including by a deleted account.")
                if user.id == current_user().id and (not active or role != "admin"):
                    raise ValueError("You cannot disable or remove administrator access from your own account.")
                user.display_name = request.form.get("display_name", "").strip() or user.username
                user.username = username
                user.department = request.form.get("department", "").strip()
                user.role = role
                user.active = active
                user.tasks_json = json.dumps(request.form.getlist("tasks"))
                if password:
                    user.set_password(password)
                audit("update", "user", user.id, f"Account details updated for {user.username}; active={active}")
                db.session.commit()
                flash("User account updated.", "success")
                return redirect(url_for("users"))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), "error")
        return render_template("user_form.html", edit_user=user)

    @app.post("/users/<int:user_id>/toggle")
    @role_required("admin")
    def user_toggle(user_id):
        user = db.get_or_404(User, user_id)
        if user.deleted:
            abort(404)
        if user.id == current_user().id:
            flash("You cannot disable your own signed-in account.", "error")
        else:
            user.active = not user.active
            audit("status", "user", user.id, f"Active: {user.active}")
            db.session.commit()
            flash("User access updated.", "success")
        return redirect(url_for("users"))

    @app.route("/users/<int:user_id>/delete", methods=["GET", "POST"])
    @role_required("admin")
    def user_delete(user_id):
        user = db.get_or_404(User, user_id)
        if user.deleted:
            abort(404)
        if request.method == "POST":
            if user.id == current_user().id:
                flash("You cannot delete your own signed-in account.", "error")
                return redirect(url_for("users"))
            if request.form.get("confirmed") != "yes":
                flash("Confirm account deletion first.", "error")
                return redirect(url_for("user_delete", user_id=user_id))
            user.deleted = True
            user.active = False
            audit("delete", "user", user.id, f"Deleted account {user.username}; ledger and audit attribution retained")
            db.session.commit()
            flash("User access removed. Past ledger and audit records are retained.", "success")
            return redirect(url_for("users"))
        return render_template("user_delete.html", edit_user=user)

    @app.get("/categories")
    @role_required("admin")
    def categories():
        items = sorted_categories(Category.query.all())
        groups = sorted_groups(Group.query.filter_by(active=True).all())
        return render_template("categories.html", categories=items, groups=groups)

    @app.post("/categories")
    @role_required("admin")
    def category_new():
        kind = request.form.get("kind", "")
        group_name = request.form.get("group_name", "").strip()
        name = request.form.get("name", "").strip()
        valid_group = kind in {"income", "expense"} and Group.query.filter_by(
            kind=kind, name=group_name, active=True
        ).first()
        if kind not in {"income", "expense"} or not group_name or not name:
            flash("Type, group, and particular name are required.", "error")
        elif not valid_group:
            flash("Select a valid group for the chosen type, or add a new one on the Groups page first.", "error")
        else:
            item = Category(
                group_id=valid_group.id,
                kind=kind,
                group_name=group_name, name=name,
                service_line=request.form.get("service_line", "").strip() or None,
                entity_name=request.form.get("entity_name", "").strip() or None,
            )
            try:
                db.session.add(item)
                db.session.flush()  # stable internal ID; public code is independently editable
                raw_code = request.form.get('code', '').strip().upper()
                if raw_code in {'', CATEGORY_PREFIX[kind] + '_0'}:
                    codes = particular_codes()
                    raw_code = next_public_code(Category, kind, item.id, 100)
                set_account_code(item, raw_code)
                audit("create", "category", item.id, f"{kind}: {name}")
                db.session.commit()
                flash(f"Account particular added with code {item.id}.", "success")
            except (IntegrityError, ValueError):
                db.session.rollback()
                flash("Enter a valid unique particular code.", "error")
        return redirect(url_for("categories"))

    @app.route('/categories/<category_id>/edit', methods=['GET', 'POST'])
    @role_required('admin')
    def category_edit(category_id):
        item = db.get_or_404(Category, category_id)
        if request.method == 'POST':
            try:
                kind = request.form.get('kind', item.kind)
                group_id = request.form.get('group_id', item.group_id)
                name = request.form.get('name', item.name).strip()
                service_line = request.form.get('service_line', item.service_line or '').strip()
                entity_name = request.form.get('entity_name', item.entity_name or '').strip()
                group = db.session.get(Group, group_id)
                if kind not in {'income', 'expense'}:
                    raise ValueError('Select a valid account type.')
                if not group or group.kind != kind or (not group.active and group.id != item.group_id):
                    raise ValueError('Select an available group for that account type.')
                if not name or len(name) > 180:
                    raise ValueError('Enter a particular name (up to 180 characters).')
                if service_line not in {'', 'Security', 'Cleaning'} or len(entity_name) > 140:
                    raise ValueError('Select a valid service line and enter a property / project up to 140 characters.')
                old = {'kind': item.kind, 'group_id': item.group_id, 'name': item.name,
                       'service_line': item.service_line, 'entity_name': item.entity_name}
                if (kind != item.kind or group.id != item.group_id) and Transaction.query.filter_by(category_id=item.id).first():
                    raise ValueError('This particular has posted entries. Create a new particular instead of changing its type or group.')
                old_code = format_id(CATEGORY_PREFIX[item.kind], particular_codes()[item.id], 4)
                raw_code = request.form.get('code', old_code).strip()
                if kind != item.kind and raw_code.upper() == old_code:
                    raw_code = str(particular_codes()[item.id])
                item.kind = kind
                item.group_id = group.id
                item.group_name = group.name
                item.name = name
                item.service_line = service_line or None
                item.entity_name = entity_name or None
                set_account_code(item, raw_code)
                audit('edit', 'category', item.id, json.dumps({'before': old, 'after': {
                    'kind': item.kind, 'group_id': item.group_id, 'name': item.name,
                    'service_line': item.service_line, 'entity_name': item.entity_name,
                    'code': format_id(CATEGORY_PREFIX[item.kind], int(raw_code.split('_')[-1]), 4),
                }}))
                db.session.commit()
                flash('Particular updated.', 'success')
                return redirect(url_for('categories'))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), 'error')
        available = Group.query.filter((Group.active == True) | (Group.id == item.group_id)).all()
        return render_template('category_edit.html', item=item, groups=sorted_groups(available))

    @app.post("/categories/<category_id>/toggle")
    @role_required("admin")
    def category_toggle(category_id):
        item = db.get_or_404(Category, category_id)
        item.active = not item.active
        audit("status", "category", item.id, f"Active: {item.active}")
        db.session.commit()
        flash("Account availability updated.", "success")
        return redirect(url_for("categories"))

    @app.post("/categories/<category_id>/delete")
    @role_required("admin")
    def category_delete(category_id):
        item = db.get_or_404(Category, category_id)
        if Transaction.query.filter_by(category_id=item.id).first():
            flash("This particular has posted entries. Hide it instead to preserve history.", "error")
            return redirect(url_for("categories"))
        name = item.name
        audit("delete", "category", item.id, f"Deleted unused particular {name}")
        db.session.delete(item)
        db.session.commit()
        flash(f"Particular {name} deleted.", "success")
        return redirect(url_for("categories"))

    @app.get("/groups")
    @role_required("admin")
    def groups():
        items = sorted_groups(Group.query.all())
        return render_template("groups.html", groups=items)

    @app.post("/groups")
    @role_required("admin")
    def group_new():
        kind = request.form.get("kind", "")
        name = request.form.get("name", "").strip()
        if kind not in {"income", "expense"} or not name:
            flash("Type and group name are required.", "error")
        elif Group.query.filter(Group.kind == kind, func.lower(Group.name) == name.lower()).first():
            flash("That group already exists for this type.", "error")
        else:
            item = Group(kind=kind, name=name)
            try:
                db.session.add(item)
                db.session.flush()  # the next IG_ id is generated here
                code = request.form.get('code', '').strip().upper()
                if code in {'', GROUP_PREFIX[kind] + '_0'}:
                    codes = group_codes()
                    code = next_public_code(Group, kind, item.id, 10)
                set_account_code(item, code)
                audit("create", "group", item.id, f"{kind}: {name}")
                db.session.commit()
                flash(f"Group added with code {item.id}.", "success")
            except (IntegrityError, ValueError):
                db.session.rollback()
                flash("Use a unique numeric group code and name.", "error")
        return redirect(url_for("groups"))

    @app.route('/groups/<group_id>/edit', methods=['GET', 'POST'])
    @role_required('admin')
    def group_edit(group_id):
        item = db.get_or_404(Group, group_id)
        if request.method == 'POST':
            try:
                kind = request.form.get('kind', item.kind)
                name = request.form.get('name', '').strip()
                if kind not in {'income', 'expense'}:
                    raise ValueError('Select a valid group type.')
                if not name or len(name) > 100:
                    raise ValueError('Enter a group name (up to 100 characters).')
                if any(g.id != item.id and g.name.lower() == name.lower() for g in Group.query.filter_by(kind=kind).all()):
                    raise ValueError('That group name is already used.')
                if kind != item.kind and Category.query.filter_by(group_id=item.id).first():
                    raise ValueError('Move this group’s particulars to other groups before changing its type. This protects existing financial entries.')
                old = {'kind': item.kind, 'name': item.name,
                       'code': format_id(GROUP_PREFIX[item.kind], group_codes()[item.id], 4)}
                raw_code = request.form.get('code', old['code']).strip()
                if kind != item.kind and raw_code.upper() == old['code']:
                    raw_code = str(group_codes()[item.id])
                item.kind = kind
                item.name = name
                set_account_code(item, raw_code)
                Category.query.filter_by(group_id=item.id).update({'group_name': name})
                audit('edit', 'group', item.id, json.dumps({'before': old, 'after': {
                    'kind': kind, 'name': name,
                    'code': format_id(GROUP_PREFIX[kind], group_codes()[item.id], 4),
                }}))
                db.session.commit()
                return redirect(url_for('groups'))
            except (ValueError, IntegrityError) as exc:
                db.session.rollback()
                flash(str(exc) if isinstance(exc, ValueError) else 'That group name is already used for this type.', 'error')
        return render_template('group_edit.html', item=item)

    @app.post("/groups/<group_id>/toggle")
    @role_required("admin")
    def group_toggle(group_id):
        item = db.get_or_404(Group, group_id)
        item.active = not item.active
        audit("status", "group", item.id, f"Active: {item.active}")
        db.session.commit()
        flash("Group availability updated.", "success")
        return redirect(url_for("groups"))

    @app.post("/groups/<group_id>/delete")
    @role_required("admin")
    def group_delete(group_id):
        item = db.get_or_404(Group, group_id)
        if Category.query.filter_by(group_id=item.id).first():
            flash("This group still has particulars. Move or hide them first.", "error")
            return redirect(url_for("groups"))
        name = item.name
        audit("delete", "group", item.id, f"Deleted empty group {name}")
        db.session.delete(item)
        db.session.commit()
        flash(f"Group {name} deleted.", "success")
        return redirect(url_for("groups"))

    @app.route('/accounts/rearrange', methods=['GET', 'POST'])
    @role_required('admin')
    def account_rearrange():
        retire_unused = request.values.get('retire_unused') == 'yes'
        plan = account_catalog_plan(retire_unused=retire_unused)
        if request.method == 'POST':
            if plan['blocked'] or request.form.get('fingerprint') != plan['fingerprint']:
                flash('Account list changed or needs manual mapping. Review the preview again.', 'error')
                return redirect(url_for('account_rearrange'))
            if request.form.get('confirmed') != 'yes':
                flash('Confirm the account changes first.', 'error')
                return redirect(url_for('account_rearrange'))
            # Take a verified snapshot before restating historic report labels.
            try:
                local_backup, external_backup, external_error = make_backup(app, force_external=True)
                if external_error:
                    raise RuntimeError('External backup failed: ' + external_error)
                db.session.rollback()
                if db.engine.dialect.name == 'sqlite':
                    db.session.execute(text('BEGIN IMMEDIATE'))
                plan = account_catalog_plan(retire_unused=retire_unused)
                if plan['blocked'] or request.form['fingerprint'] != plan['fingerprint']:
                    raise ValueError('Account list changed during backup. Nothing was updated; review again.')
                before = db.session.query(func.count(Transaction.id), func.sum(Transaction.total)).one()
                apply_account_catalog(plan)
                after = db.session.query(func.count(Transaction.id), func.sum(Transaction.total)).one()
                if before != after:
                    raise RuntimeError('Ledger totals changed unexpectedly. Account update cancelled.')
                for model, codes in ((Group, group_codes()), (Category, particular_codes())):
                    for kind in ('income', 'expense'):
                        values = [codes[item.id] for item in model.query.filter_by(kind=kind).all()]
                        if len(values) != len(set(values)):
                            raise RuntimeError('Duplicate account codes detected. Account update cancelled.')
                db.session.commit()
                flash(f'Account chart updated. Ledger entries retained. Safety backup: {local_backup.name}' +
                      (f'; external copy: {external_backup}' if external_backup else ''), 'success')
                return redirect(url_for('categories'))
            except (RuntimeError, ValueError, IntegrityError, OperationalError) as exc:
                db.session.rollback()
                flash(str(exc), 'error')
                return redirect(url_for('account_rearrange'))
        return render_template('account_rearrange.html', plan=plan,
                               group_count=len(CATALOG_GROUPS), particular_count=len(CATALOG_PARTICULARS))

    @app.post("/backup")
    @role_required("admin")
    def backup_now():
        path, external_path, external_error = make_backup(app, force_external=True)
        audit("backup", "database", None, path.name)
        db.session.commit()
        if external_error:
            flash(f"Local backup created, but the external backup failed: {external_error}", "error")
        elif external_path:
            flash(f"Backup created locally and at {external_path}", "success")
        else:
            flash(f"Local backup created: {path.name}. Configure an external backup for disaster recovery.", "success")
        return redirect(url_for("dashboard"))

    @app.route('/backup/settings', methods=['GET', 'POST'])
    @role_required('admin')
    def backup_preferences():
        if request.method == 'POST':
            try:
                save_settings(DATA_ROOT, request.form.get('interval_minutes', ''))
                audit('backup_settings', 'database', None, 'Backup interval changed')
                db.session.commit()
                flash('Backup schedule saved.', 'success')
                return redirect(url_for('backup_preferences'))
            except (ValueError, OSError) as error:
                flash(str(error), 'error')
        return render_template('backup_settings.html', settings=read_settings(DATA_ROOT),
                               status=read_status(DATA_ROOT),
                               external_configured=(DATA_ROOT / 'backup-target.txt').exists())

    @app.route("/account/password", methods=["GET", "POST"])
    @role_required("admin")
    def change_password():
        user = current_user()
        if request.method == "POST":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            if not check_password_hash(user.password_hash, current):
                flash("Current password is incorrect.", "error")
            elif len(new) < 6:
                flash("New password must be at least 6 characters.", "error")
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


@serialized_backup
def make_backup(app, force_external=False, local_only=False):
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not database_uri.startswith("sqlite:///"):
        raise RuntimeError("Automatic file backup is only available for SQLite.")
    source = Path(database_uri[len("sqlite:///"):])
    if not source.is_absolute():
        source = DATA_ROOT / source
    destination = DATA_ROOT / "backups" / f"kys_finance_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    temporary = destination.with_suffix(".tmp")
    destination.parent.mkdir(exist_ok=True)
    with closing(sqlite3.connect(source)) as source_db, closing(sqlite3.connect(temporary)) as backup_db:
        source_db.backup(backup_db)
        if backup_db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite backup integrity check failed.")
    temporary.replace(destination)
    backups = sorted(destination.parent.glob("kys_finance_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    cutoff = time.time() - 30 * 24 * 60 * 60
    for old in backups[60:]:
        if old.stat().st_mtime < cutoff:
            old.unlink(missing_ok=True)
    external_path = None
    external_error = None
    if not local_only and (DATA_ROOT / "backup-target.txt").exists():
        try:
            external_path = copy_external_backup(destination, force=force_external)
        except (OSError, RuntimeError, sqlite3.DatabaseError) as exc:
            external_error = str(exc)
            app.logger.exception("External backup failed; local backup remains available")
    record_status(DATA_ROOT, local=destination, external=external_path, error=external_error,
                  external_attempted=not local_only and (DATA_ROOT / 'backup-target.txt').exists())
    return destination, external_path, external_error


def copy_external_backup(local_backup, force=False):
    from backup_copy import copy_snapshot  # Included in frozen dependency graph.
    arguments = [str(DATA_ROOT), str(local_backup), '1' if force else '0']
    if getattr(sys, 'frozen', False):
        command = [sys.executable, '--copy-backup'] + arguments
    else:
        command = [sys.executable, str(Path(__file__).with_name('backup_copy.py'))] + arguments
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired:
        raise RuntimeError('Network backup timed out after 30 seconds. The local backup is safe.')
    try:
        response = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError('External backup worker could not start.')
    if result.returncode or 'error' in response:
        raise RuntimeError(response.get('error', 'External backup failed.'))
    return Path(response['path'])


def start_backup_worker(app):
    if getattr(app, "_backup_started", False):
        return
    app._backup_started = True

    def worker():
        last_attempt = 0
        while True:
            if time.monotonic() - last_attempt >= read_settings(DATA_ROOT)['interval_minutes'] * 60 or not last_attempt:
                try:
                    make_backup(app)
                except Exception as error:
                    app.logger.exception("Scheduled backup failed")
                    try:
                        record_status(DATA_ROOT, local_error=str(error))
                    except OSError:
                        app.logger.exception('Could not record backup failure')
                last_attempt = time.monotonic()
            time.sleep(5)

    threading.Thread(target=worker, daemon=True, name="sqlite-backup").start()


def get_or_create_group(kind, name):
    group = Group.query.filter_by(kind=kind, name=name).first()
    if not group:
        group = Group(kind=kind, name=name)
        db.session.add(group)
        db.session.flush()
    return group


def create_category(kind, group_name, name, service=None, entity=None):
    group = get_or_create_group(kind, group_name)
    item = Category(group_id=group.id, kind=kind, group_name=group_name, name=name,
                    service_line=service, entity_name=entity)
    db.session.add(item)
    db.session.flush()
    return item


def seed_database():
    if not User.query.first() and os.environ.get("KYS_COMPANY_MODE") != "1":
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
        # New installations use the reviewed workbook catalog. Existing company
        # databases are never silently recoded on application startup.
        groups_by_code = {}
        for kind, code, name in CATALOG_GROUPS:
            group = Group(kind=kind, name=name)
            db.session.add(group)
            db.session.flush()
            db.session.add(AuditLog(action='group_code', entity_type='group',
                                    entity_id=group.id, details=str(int(code.split('_')[1]))))
            groups_by_code[code] = group
        for kind, group_code, code, name in CATALOG_PARTICULARS:
            group = groups_by_code[group_code]
            service = ('Security' if name.startswith('Security Service ') else
                       'Cleaning' if name.startswith('Cleaning Service ') else None)
            item = Category(kind=kind, group_id=group.id, group_name=group.name,
                            name=name, service_line=service)
            db.session.add(item)
            db.session.flush()
            db.session.add(AuditLog(action='account_code', entity_type='category',
                                    entity_id=item.id, details=str(int(code.split('_')[1]))))

    # Link any particular that predates group IDs to its group.
    for cat in Category.query.filter(Category.group_id.is_(None)).all():
        cat.group_id = get_or_create_group(cat.kind, cat.group_name).id

    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
