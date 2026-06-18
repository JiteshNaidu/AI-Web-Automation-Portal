import sqlite3
from datetime import datetime

DB_NAME = "web_automation.db"


# ===============================
# DATABASE CONNECTION
# ===============================
def get_connection():
    return sqlite3.connect(DB_NAME)


# ===============================
# CREATE TABLES
# ===============================
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Export History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ExportHistory (
            ExportID INTEGER PRIMARY KEY AUTOINCREMENT,
            ReportName TEXT NOT NULL,
            ExportDate TEXT,
            Status TEXT,
            FilePath TEXT,
            EmailStatus TEXT
        )
    """)

    # Click Tracking Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ClickTracking (
            ClickID INTEGER PRIMARY KEY AUTOINCREMENT,
            PageName TEXT,
            ControlName TEXT,
            ActionName TEXT,
            ClickDateTime TEXT
        )
    """)

    # URL Master Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS URLMaster (
            URLID INTEGER PRIMARY KEY AUTOINCREMENT,
            ApplicationName TEXT NOT NULL,
            URLName TEXT NOT NULL,
            URL TEXT NOT NULL,
            Description TEXT,
            Category TEXT,
            IsActive INTEGER DEFAULT 1,
            CreatedDate TEXT
        )
    """)

    conn.commit()
    conn.close()


# ===============================
# EXPORT HISTORY FUNCTIONS
# ===============================
def add_export_history(report_name, status, file_path, email_status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ExportHistory
        (ReportName, ExportDate, Status, FilePath, EmailStatus)
        VALUES (?, ?, ?, ?, ?)
    """, (
        report_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status,
        file_path,
        email_status
    ))

    conn.commit()
    conn.close()


def get_export_history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ReportName, ExportDate, Status, FilePath, EmailStatus
        FROM ExportHistory
        ORDER BY ExportID DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


# ===============================
# CLICK TRACKING FUNCTIONS
# ===============================
def track_click(page_name, control_name, action_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ClickTracking
        (PageName, ControlName, ActionName, ClickDateTime)
        VALUES (?, ?, ?, ?)
    """, (
        page_name,
        control_name,
        action_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_click_history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT PageName, ControlName, ActionName, ClickDateTime
        FROM ClickTracking
        ORDER BY ClickID DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


# ===============================
# URL MASTER FUNCTIONS
# ===============================
def add_url(application_name, url_name, url, description, category):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO URLMaster
        (ApplicationName, URLName, URL, Description, Category, IsActive, CreatedDate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        application_name,
        url_name,
        url,
        description,
        category,
        1,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_urls():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT URLID, ApplicationName, URLName, URL, Description, Category, IsActive, CreatedDate
        FROM URLMaster
        ORDER BY URLID DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def delete_url(url_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM URLMaster
        WHERE URLID = ?
    """, (url_id,))

    conn.commit()
    conn.close()


def update_url_status(url_id, is_active):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE URLMaster
        SET IsActive = ?
        WHERE URLID = ?
    """, (is_active, url_id))

    conn.commit()
    conn.close()