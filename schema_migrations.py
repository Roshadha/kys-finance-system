"""Legacy account-ID migration shared by startup and staged backup restore."""
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import closing
from sqlalchemy.schema import CreateTable, CreateIndex
GROUP_PREFIX = {"income": "IG", "expense": "EG"}
CATEGORY_PREFIX = {"income": "IP", "expense": "EP"}
def format_id(prefix, number, width):
    return f"{prefix}_{number:0{width}d}"
def numeric_part(value):
    return int(str(value).split("_")[-1])

def migrate_legacy_ids(engine, backup_directory, tables, group_order, create_table=CreateTable):
    """Atomically upgrade legacy IDs, preserving cash records and audit links."""
    if engine.dialect.name != "sqlite":
        return
    db_path = engine.url.database
    if not db_path or db_path == ":memory:" or not Path(db_path).exists():
        return
    con = sqlite3.connect(db_path, isolation_level=None, timeout=30)
    migrated = False
    try:
        # Reserve the write lock before taking a snapshot or reading mapping data.
        # A separate reader can still take a consistent SQLite backup (including WAL).
        con.execute("BEGIN IMMEDIATE")
        cols = {row[1]: (row[2] or "").upper() for row in con.execute("PRAGMA table_info(category)")}
        if not cols or not (cols["id"].startswith("INT") or "code" in cols):
            con.execute("ROLLBACK")
            return
        backup_dir = Path(backup_directory) if backup_directory else Path(db_path).parent / "migration-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"pre-code-migration-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(backup_file)) as snapshot:
            source.backup(snapshot)
            if snapshot.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Migration backup failed validation; no accounts were changed.")

        group_rows = con.execute('SELECT id, kind, name, active FROM "group"').fetchall()
        rank = {key: i for i, key in enumerate(group_order)}
        group_rows.sort(key=lambda r: (rank.get((r[1], r[2]), len(rank)), numeric_part(r[0])))
        cat_rows = con.execute(
            "SELECT id, kind, group_name, name, service_line, entity_name, active, code FROM category"
        ).fetchall()
        cat_rows.sort(key=lambda r: numeric_part(r[0]))

        group_ids, old_group_ids, new_groups, counters = {}, {}, [], {}
        def add_group(kind, name, active):
            counters[kind] = counters.get(kind, 0) + 1
            gid = format_id(GROUP_PREFIX[kind], counters[kind] * 100, 0)
            group_ids[(kind, name)] = gid
            new_groups.append((gid, kind, name, active))
            return gid
        for old_id, kind, name, active in group_rows:
            old_group_ids[str(old_id)] = add_group(kind, name, active)
        for _, kind, gname, *_rest in cat_rows:
            if (kind, gname) not in group_ids:
                add_group(kind, gname, 1)

        cat_ids, legacy_codes, new_cats, counters = {}, {}, [], {}
        for old_id, kind, gname, name, service, entity, active, code in cat_rows:
            counters[kind] = counters.get(kind, 0) + 1
            cid = format_id(CATEGORY_PREFIX[kind], counters[kind] * 10, 4)
            cat_ids[str(old_id)] = cid
            legacy_codes[str(old_id)] = code
            new_cats.append((cid, group_ids[(kind, gname)], kind, gname, name, service, entity, active))

        def read_table(name):
            cursor = con.execute(f'SELECT * FROM "{name}"')
            return [column[0] for column in cursor.description], cursor.fetchall()

        txn_cols, txns = read_table("transaction")
        audit_cols, audits = read_table("audit_log")
        category_index = txn_cols.index("category_id")
        converted_txns = []
        for row in txns:
            row = list(row)
            row[category_index] = cat_ids[str(row[category_index])]
            converted_txns.append(row)
        entity_type_index = audit_cols.index("entity_type")
        entity_id_index = audit_cols.index("entity_id")
        converted_audits = []
        for row in audits:
            row = list(row)
            value = row[entity_id_index]
            mapping = {"category": cat_ids, "group": old_group_ids}.get(row[entity_type_index], {})
            row[entity_id_index] = mapping.get(str(value), str(value)) if value is not None else None
            converted_audits.append(row)

        # All DDL and data changes participate in the same transaction. No user,
        # vehicle or adjustment records are rebuilt.
        for name in ("transaction", "category", "group", "audit_log"):
            con.execute(f'DROP TABLE "{name}"')
        for name in ("group", "category", "transaction", "audit_log"):
            table = tables[name]
            con.execute(str(create_table(table).compile(dialect=engine.dialect)))
            for index in table.indexes:
                con.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
        con.executemany('INSERT INTO "group" (id, kind, name, active) VALUES (?,?,?,?)', new_groups)
        con.executemany(
            "INSERT INTO category (id, group_id, kind, group_name, name, service_line, entity_name, active) "
            "VALUES (?,?,?,?,?,?,?,?)", new_cats)
        for table_name, columns, rows in (
                ("transaction", txn_cols, converted_txns), ("audit_log", audit_cols, converted_audits)):
            marks = ",".join("?" * len(columns))
            names = ",".join(f'"{column}"' for column in columns)
            con.executemany(f'INSERT INTO "{table_name}" ({names}) VALUES ({marks})', rows)

        # Keep old account codes as a historical cross-reference even though the
        # UI now uses automatic IDs and no longer asks for a separate account code.
        con.execute("CREATE TABLE account_code_migration ("
                    "entity_type TEXT NOT NULL, old_id TEXT NOT NULL, new_id TEXT NOT NULL, "
                    "legacy_code TEXT, PRIMARY KEY (entity_type, old_id))")
        con.executemany("INSERT INTO account_code_migration VALUES (?,?,?,?)",
                        [("group", old, new, None) for old, new in old_group_ids.items()] +
                        [("category", old, new, legacy_codes[old]) for old, new in cat_ids.items()])
        if con.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("Account migration found a broken data reference; changes were rolled back.")
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Account migration failed integrity checks; changes were rolled back.")
        con.execute("COMMIT")
        migrated = True
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    if migrated:
        engine.dispose()

