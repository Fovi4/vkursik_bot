import sqlite3
from datetime import datetime
from os import getenv


DB_NAME = getenv("DB_PATH", "applications.db")


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                telegram_id INTEGER NOT NULL,
                username TEXT,

                name TEXT NOT NULL,
                faculty TEXT NOT NULL,
                course TEXT NOT NULL,
                direction TEXT NOT NULL,
                experience TEXT,
                portfolio TEXT,
                motivation TEXT,

                status TEXT NOT NULL DEFAULT 'new',

                reviewed_by_id INTEGER,
                reviewed_by_name TEXT,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()


def create_application(
    telegram_id,
    username,
    name,
    faculty,
    course,
    direction,
    experience,
    portfolio,
    motivation
):
    now = datetime.now().isoformat(timespec="seconds")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO applications (
                telegram_id,
                username,
                name,
                faculty,
                course,
                direction,
                experience,
                portfolio,
                motivation,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_id,
            username,
            name,
            faculty,
            course,
            direction,
            experience,
            portfolio,
            motivation,
            "new",
            now,
            now
        ))

        conn.commit()

        return cursor.lastrowid


def get_application(application_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,)
        )

        application = cursor.fetchone()

        return dict(application) if application else None


def update_application_status(
    application_id,
    status,
    reviewed_by_id,
    reviewed_by_name
):
    now = datetime.now().isoformat(timespec="seconds")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE applications

            SET status = ?,
                reviewed_by_id = ?,
                reviewed_by_name = ?,
                updated_at = ?

            WHERE id = ?
        """, (
            status,
            reviewed_by_id,
            reviewed_by_name,
            now,
            application_id
        ))

        conn.commit()


def get_all_applications():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM applications
            ORDER BY id DESC
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

def get_application_stats():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*)
            FROM applications
            GROUP BY status
        """)

        rows = cursor.fetchall()

        stats = {
            "new": 0,
            "interview": 0,
            "accepted": 0,
            "rejected": 0
        }

        for status, count in rows:
            stats[status] = count

        return stats


def get_applications_by_status(status):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM applications
            WHERE status = ?
            ORDER BY id DESC
        """, (status,))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]