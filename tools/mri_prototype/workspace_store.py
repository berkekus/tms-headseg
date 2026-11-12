"""Local Workbench accounts, workstation setup and study records."""

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import file_digest, scrypt
from hmac import compare_digest
import json
from pathlib import Path
import re
from secrets import token_bytes
import sqlite3
from uuid import uuid4


ROLES = {"physician": "Physician", "technical": "Technical Team"}
MIN_PASSWORD_LENGTH = 8
STUDY_KINDS = {"prediction": "Tissue result", "head": "Head model"}


@dataclass(frozen=True)
class Account:
    id: str
    username: str
    role: str


def fingerprint(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def result_identity(model):
    files = [model.labels[0]]
    if model.mesh_path is not None:
        files.extend((model.mesh_path, model.volume.path))
    return ":".join(fingerprint(path) for path in dict.fromkeys(files))


def password_hash(password, salt):
    return scrypt(password.encode("utf-8"), salt=salt, n=2**17, r=8, p=1, maxmem=160 * 1024**2)


class WorkspaceStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / "workbench.sqlite3"
        with self.connection() as database:
            database.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    role TEXT NOT NULL CHECK (role IN ('physician','technical')),
                    salt BLOB NOT NULL, password_hash BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS studies (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES accounts(id),
                    source TEXT NOT NULL, digest TEXT NOT NULL, active_result TEXT,
                    updated INTEGER NOT NULL DEFAULT (unixepoch()), UNIQUE(owner, digest)
                );
                CREATE TABLE IF NOT EXISTS results (
                    id TEXT PRIMARY KEY, study TEXT NOT NULL REFERENCES studies(id),
                    kind TEXT NOT NULL CHECK (kind IN ('prediction','head')),
                    path TEXT NOT NULL, digest TEXT NOT NULL, assume_mm INTEGER NOT NULL,
                    active_view TEXT, UNIQUE(study, kind, path, digest)
                );
                CREATE TABLE IF NOT EXISTS views (
                    result TEXT NOT NULL REFERENCES results(id), name TEXT NOT NULL COLLATE NOCASE,
                    state TEXT NOT NULL, PRIMARY KEY(result, name)
                );
            """)

    @contextmanager
    def connection(self):
        database = sqlite3.connect(self.path)
        try:
            database.row_factory = sqlite3.Row
            database.execute("PRAGMA foreign_keys = ON")
            with database:
                yield database
        finally:
            database.close()

    def has_technical_account(self):
        with self.connection() as database:
            return self.technical_account_exists(database)

    @staticmethod
    def technical_account_exists(database):
        return database.execute("SELECT 1 FROM accounts WHERE role='technical' LIMIT 1").fetchone() is not None

    @staticmethod
    def require_account(database, account, role=None):
        if account is None or (role is not None and account.role != role):
            raise PermissionError("This account cannot perform the requested action.")
        current = database.execute("SELECT username, role FROM accounts WHERE id=?", (account.id,)).fetchone()
        if current is None or tuple(current) != (account.username, account.role):
            raise PermissionError("Sign in again to continue.")

    def create_account(self, username, password, role, *, actor=None):
        username = username.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", username):
            raise ValueError("Use 3–64 letters, numbers, dots, hyphens or underscores for the account name.")
        if not MIN_PASSWORD_LENGTH <= len(password) <= 256:
            raise ValueError(f"Use a password of {MIN_PASSWORD_LENGTH}–256 characters.")
        if role not in ROLES:
            raise ValueError("Select a valid workspace role.")
        salt = token_bytes(16)
        digest = password_hash(password, salt)
        account = Account(uuid4().hex, username, role)
        with self.connection() as database:
            database.execute("BEGIN IMMEDIATE")
            if actor is not None:
                self.require_account(database, actor, "technical")
            elif role == "technical" and self.technical_account_exists(database):
                raise PermissionError("Ask an existing Technical Team member to create your technical account.")
            try:
                database.execute("INSERT INTO accounts VALUES (?, ?, ?, ?, ?)",
                                 (account.id, username, role, salt, digest))
            except sqlite3.IntegrityError as error:
                raise ValueError("That account name already exists.") from error
        return account

    def authenticate(self, username, password, role):
        if role not in ROLES or len(username) > 64 or len(password) > 256:
            return None
        with self.connection() as database:
            row = database.execute("SELECT * FROM accounts WHERE username=?", (username.strip(),)).fetchone()
        digest = password_hash(password, row["salt"] if row else bytes(16))
        if row and compare_digest(digest, row["password_hash"]) and role == row["role"]:
            return Account(row["id"], row["username"], row["role"])
        return None

    def setup(self, account):
        with self.connection() as database:
            self.require_account(database, account)
            row = database.execute("SELECT value FROM settings WHERE key='workstation'").fetchone()
            return json.loads(row["value"]) if row else None

    def save_setup(self, account, settings):
        with self.connection() as database:
            self.require_account(database, account, "technical")
            database.execute("INSERT OR REPLACE INTO settings VALUES ('workstation', ?)", (json.dumps(settings),))

    def studies(self, account):
        with self.connection() as database:
            self.require_account(database, account)
            rows = database.execute("""
                SELECT s.*, r.kind, r.active_view FROM studies s LEFT JOIN results r ON s.active_result=r.id
                WHERE s.owner=? ORDER BY s.updated DESC, s.id
            """, (account.id,))
            return [dict(row) for row in rows]

    def remember_source(self, account, source, digest):
        with self.connection() as database:
            self.require_account(database, account)
            database.execute("""
                INSERT INTO studies(id, owner, source, digest) VALUES (?, ?, ?, ?)
                ON CONFLICT(owner, digest) DO UPDATE SET source=excluded.source, updated=unixepoch()
            """, (uuid4().hex, account.id, str(source), digest))
            return database.execute("SELECT id FROM studies WHERE owner=? AND digest=?",
                                    (account.id, digest)).fetchone()["id"]

    def add_result(self, account, study, kind, path, digest, assume_mm=False):
        with self.connection() as database:
            self.require_account(database, account)
            database.execute("BEGIN IMMEDIATE")
            self.owned_study(database, account, study)
            database.execute("""
                INSERT INTO results(id, study, kind, path, digest, assume_mm) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(study, kind, path, digest) DO NOTHING
            """, (uuid4().hex, study, kind, str(path), digest, assume_mm))
            result = database.execute(
                "SELECT id FROM results WHERE study=? AND kind=? AND path=? AND digest=?",
                (study, kind, str(path), digest)).fetchone()["id"]
            database.execute("UPDATE studies SET active_result=?, updated=unixepoch() WHERE id=?", (result, study))
            return result

    @staticmethod
    def owned_study(database, account, study):
        row = database.execute("SELECT * FROM studies WHERE id=? AND owner=?", (study, account.id)).fetchone()
        if row is None:
            raise PermissionError("This study is unavailable for this account.")
        return row

    @staticmethod
    def owned_result(database, account, result):
        row = database.execute("""
            SELECT r.* FROM results r JOIN studies s ON r.study=s.id WHERE r.id=? AND s.owner=?
        """, (result, account.id)).fetchone()
        if row is None:
            raise PermissionError("This result is unavailable for this account.")
        return row

    def study(self, account, study):
        with self.connection() as database:
            self.require_account(database, account)
            row = dict(self.owned_study(database, account, study))
            results = database.execute("SELECT * FROM results WHERE study=? ORDER BY rowid DESC", (study,))
            return row, [dict(result) for result in results]

    def activate_result(self, account, study, result):
        with self.connection() as database:
            self.require_account(database, account)
            self.owned_study(database, account, study)
            if self.owned_result(database, account, result)["study"] != study:
                raise PermissionError("The selected result belongs to another study.")
            database.execute("UPDATE studies SET active_result=?, updated=unixepoch() WHERE id=?", (result, study))

    def views(self, account, result):
        with self.connection() as database:
            self.require_account(database, account)
            row = self.owned_result(database, account, result)
            rows = database.execute("SELECT name, state FROM views WHERE result=? ORDER BY name", (result,))
            return row["active_view"], {entry["name"]: json.loads(entry["state"]) for entry in rows}

    def save_view(self, account, result, name, state, *, replace=False):
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("Enter a view name of 1–80 characters.")
        with self.connection() as database:
            self.require_account(database, account)
            database.execute("BEGIN IMMEDIATE")
            self.owned_result(database, account, result)
            try:
                database.execute("""
                    INSERT INTO views VALUES (?, ?, ?) ON CONFLICT(result, name) DO UPDATE
                    SET state=excluded.state WHERE ?
                """, (result, name, json.dumps(state, allow_nan=False), replace))
                if not database.execute("SELECT changes()").fetchone()[0]:
                    raise ValueError("That view name already exists. Enter a different name.")
            except sqlite3.IntegrityError as error:
                raise ValueError("The view could not be saved.") from error
            database.execute("UPDATE results SET active_view=? WHERE id=?", (name, result))
        return name

    def activate_view(self, account, result, name):
        with self.connection() as database:
            self.require_account(database, account)
            self.owned_result(database, account, result)
            if not database.execute("SELECT 1 FROM views WHERE result=? AND name=?", (result, name)).fetchone():
                raise ValueError("The saved view is unavailable.")
            database.execute("UPDATE results SET active_view=? WHERE id=?", (name, result))
