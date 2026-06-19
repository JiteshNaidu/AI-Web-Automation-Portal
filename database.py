import sqlite3
from datetime import datetime, timedelta
import hashlib
import os
import binascii
import time

DB_NAME = "web_automation.db"


# ===============================
# DATABASE CONNECTION
# ===============================
def get_connection():
    conn = sqlite3.connect(
        DB_NAME,
        timeout=30,
        check_same_thread=False
    )

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


# ===============================
# RETRY HELPER FOR SQLITE LOCKS
# ===============================
def execute_with_retry(operation, retries=5, delay=0.25):
    last_error = None

    for _ in range(retries):
        try:
            return operation()
        except sqlite3.OperationalError as error:
            last_error = error

            if "locked" in str(error).lower():
                time.sleep(delay)
                continue

            raise error

    raise last_error


# ===============================
# PASSWORD HASHING
# ===============================
def hash_password(password):
    salt = os.urandom(16)
    iterations = 120000

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations
    )

    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        binascii.hexlify(salt).decode("utf-8"),
        binascii.hexlify(password_hash).decode("utf-8")
    )


def verify_password(password, stored_password):
    if stored_password is None:
        return False

    # New hashed password format
    if stored_password.startswith("pbkdf2_sha256$"):
        try:
            parts = stored_password.split("$")
            iterations = int(parts[1])
            salt = binascii.unhexlify(parts[2])
            stored_hash = parts[3]

            test_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations
            )

            test_hash_hex = binascii.hexlify(test_hash).decode("utf-8")

            return test_hash_hex == stored_hash

        except Exception:
            return False

    # Legacy support for old plain-text users
    return password == stored_password


# ===============================
# MIGRATION HELPER
# ===============================
def add_column_if_missing(cursor, table_name, column_name, column_definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


# ===============================
# CREATE TABLES
# ===============================
def create_tables():
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS UserMaster (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                FullName TEXT NOT NULL,
                Email TEXT NOT NULL UNIQUE,
                Password TEXT NOT NULL,
                Role TEXT DEFAULT 'User',
                IsActive INTEGER DEFAULT 1,
                CreatedDate TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SessionMaster (
                SessionID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserEmail TEXT NOT NULL,
                LoginTime TEXT,
                LogoutTime TEXT,
                IsActive INTEGER DEFAULT 1
            )
        """)

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ClickTracking (
                ClickID INTEGER PRIMARY KEY AUTOINCREMENT,
                PageName TEXT,
                ControlName TEXT,
                ActionName TEXT,
                ClickDateTime TEXT
            )
        """)

        add_column_if_missing(cursor, "ClickTracking", "UserEmail", "TEXT")
        add_column_if_missing(cursor, "ClickTracking", "SessionID", "INTEGER")
        add_column_if_missing(cursor, "ClickTracking", "URLID", "INTEGER")
        add_column_if_missing(cursor, "ClickTracking", "URLName", "TEXT")
        add_column_if_missing(cursor, "ClickTracking", "ApplicationName", "TEXT")

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

        ensure_default_admin()

    execute_with_retry(operation)


# ===============================
# DEFAULT ADMIN
# ===============================
def ensure_default_admin():
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM UserMaster
            WHERE Role = 'Admin'
        """)

        admin_count = cursor.fetchone()[0]

        if admin_count == 0:
            cursor.execute("""
                INSERT INTO UserMaster
                (FullName, Email, Password, Role, IsActive, CreatedDate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "Default Admin",
                "admin@portal.com",
                hash_password("Admin@123"),
                "Admin",
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        conn.commit()
        conn.close()

    execute_with_retry(operation)


# ===============================
# USER FUNCTIONS
# ===============================
def register_user(full_name, email, password):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO UserMaster
                (FullName, Email, Password, Role, IsActive, CreatedDate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                full_name.strip(),
                email.lower().strip(),
                hash_password(password.strip()),
                "User",
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn.commit()
            conn.close()

            return True, "User registered successfully."

        except sqlite3.IntegrityError:
            conn.close()
            return False, "Email already exists. Please use another email."

        except Exception as error:
            conn.close()
            return False, f"Registration failed: {error}"

    return execute_with_retry(operation)


def validate_user(email, password, required_role=None):
    conn = get_connection()
    cursor = conn.cursor()

    if required_role:
        cursor.execute("""
            SELECT UserID, FullName, Email, Password, Role
            FROM UserMaster
            WHERE lower(Email) = lower(?)
            AND Role = ?
            AND IsActive = 1
        """, (
            email.strip(),
            required_role
        ))
    else:
        cursor.execute("""
            SELECT UserID, FullName, Email, Password, Role
            FROM UserMaster
            WHERE lower(Email) = lower(?)
            AND IsActive = 1
        """, (
            email.strip(),
        ))

    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, None

    user_id = user[0]
    full_name = user[1]
    user_email = user[2]
    stored_password = user[3]
    role = user[4]

    is_valid = verify_password(password.strip(), stored_password)

    # Upgrade old plain-text password to hashed password
    if is_valid and not stored_password.startswith("pbkdf2_sha256$"):
        cursor.execute("""
            UPDATE UserMaster
            SET Password = ?
            WHERE UserID = ?
        """, (
            hash_password(password.strip()),
            user_id
        ))
        conn.commit()

    conn.close()

    if is_valid:
        return True, {
            "FullName": full_name,
            "Email": user_email,
            "Role": role
        }

    return False, None


def change_password(email, old_password, new_password):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT UserID, Password
            FROM UserMaster
            WHERE lower(Email) = lower(?)
            AND IsActive = 1
        """, (
            email.strip(),
        ))

        user = cursor.fetchone()

        if not user:
            conn.close()
            return False, "User not found."

        user_id = user[0]
        stored_password = user[1]

        if not verify_password(old_password.strip(), stored_password):
            conn.close()
            return False, "Current password is incorrect."

        cursor.execute("""
            UPDATE UserMaster
            SET Password = ?
            WHERE UserID = ?
        """, (
            hash_password(new_password.strip()),
            user_id
        ))

        conn.commit()
        conn.close()

        return True, "Password changed successfully. Please login again."

    return execute_with_retry(operation)


def get_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT UserID, FullName, Email, Role, IsActive, CreatedDate
        FROM UserMaster
        ORDER BY UserID DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def update_user_role(user_id, role):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE UserMaster
            SET Role = ?
            WHERE UserID = ?
        """, (
            role,
            user_id
        ))

        conn.commit()
        conn.close()

    execute_with_retry(operation)


# ===============================
# SESSION FUNCTIONS
# ===============================
def start_user_session(user_email):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO SessionMaster
            (UserEmail, LoginTime, LogoutTime, IsActive)
            VALUES (?, ?, ?, ?)
        """, (
            user_email.lower().strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            None,
            1
        ))

        session_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return session_id

    return execute_with_retry(operation)


def end_user_session(session_id):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE SessionMaster
            SET LogoutTime = ?,
                IsActive = 0
            WHERE SessionID = ?
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session_id
        ))

        conn.commit()
        conn.close()

    execute_with_retry(operation)


def get_session_details(session_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SessionID, UserEmail, LoginTime, LogoutTime, IsActive
        FROM SessionMaster
        WHERE SessionID = ?
    """, (
        session_id,
    ))

    row = cursor.fetchone()
    conn.close()

    return row


def get_current_session_duration_seconds(session_id):
    session = get_session_details(session_id)

    if not session:
        return 0

    login_time = session[2]

    if not login_time:
        return 0

    login_dt = datetime.strptime(login_time, "%Y-%m-%d %H:%M:%S")
    now_dt = datetime.now()

    return int((now_dt - login_dt).total_seconds())


# ===============================
# EXPORT HISTORY FUNCTIONS
# ===============================
def add_export_history(report_name, status, file_path, email_status):
    def operation():
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

    execute_with_retry(operation)


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
def track_click(
    page_name,
    control_name,
    action_name,
    user_email=None,
    session_id=None,
    url_id=None,
    url_name=None,
    application_name=None
):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ClickTracking
            (
                PageName,
                ControlName,
                ActionName,
                ClickDateTime,
                UserEmail,
                SessionID,
                URLID,
                URLName,
                ApplicationName
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page_name,
            control_name,
            action_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_email,
            session_id,
            url_id,
            url_name,
            application_name
        ))

        conn.commit()
        conn.close()

    execute_with_retry(operation)


def get_click_history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            PageName,
            ControlName,
            ActionName,
            ClickDateTime,
            UserEmail,
            SessionID,
            URLID,
            URLName,
            ApplicationName
        FROM ClickTracking
        ORDER BY ClickID DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_current_session_click_count(session_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM ClickTracking
        WHERE SessionID = ?
    """, (
        session_id,
    ))

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_site_total_click_count(url_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM ClickTracking
        WHERE URLID = ?
    """, (
        url_id,
    ))

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_site_session_click_count(url_id, session_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM ClickTracking
        WHERE URLID = ?
        AND SessionID = ?
    """, (
        url_id,
        session_id
    ))

    count = cursor.fetchone()[0]
    conn.close()

    return count


# ===============================
# URL MASTER FUNCTIONS
# ===============================
def add_url(application_name, url_name, url, description, category):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO URLMaster
            (ApplicationName, URLName, URL, Description, Category, IsActive, CreatedDate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            application_name.strip(),
            url_name.strip(),
            url.strip(),
            description.strip(),
            category.strip(),
            1,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

    execute_with_retry(operation)


def get_urls():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT URLID, ApplicationName, URLName, URL, Description, Category, IsActive, CreatedDate
        FROM URLMaster
        WHERE IsActive = 1
        ORDER BY URLID DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_all_urls():
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


def update_url_status(url_id, is_active):
    def operation():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE URLMaster
            SET IsActive = ?
            WHERE URLID = ?
        """, (
            is_active,
            url_id
        ))

        conn.commit()
        conn.close()

    execute_with_retry(operation)


# ===============================
# CSV EXPORT DATA FUNCTIONS
# ===============================
def get_daily_active_export_rows():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT UserEmail, LoginTime
        FROM SessionMaster
        WHERE LoginTime IS NOT NULL
    """)

    rows = cursor.fetchall()
    conn.close()

    date_users = {}

    for user_email, login_time in rows:
        try:
            login_date = datetime.strptime(login_time, "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            continue

        if login_date not in date_users:
            date_users[login_date] = set()

        date_users[login_date].add(user_email)

    export_rows = []

    for date_value in sorted(date_users.keys()):
        daily_active_users = len(date_users[date_value])

        weekly_users = set()
        start_date = date_value - timedelta(days=6)

        for check_date, users in date_users.items():
            if start_date <= check_date <= date_value:
                weekly_users.update(users)

        export_rows.append((
            date_value.strftime("%m/%d/%Y"),
            daily_active_users,
            len(weekly_users)
        ))

    return export_rows


def get_sessions_export_rows():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            SessionID,
            UserEmail,
            LoginTime,
            LogoutTime,
            IsActive
        FROM SessionMaster
        ORDER BY LoginTime DESC
    """)

    sessions = cursor.fetchall()
    export_rows = []

    for session in sessions:
        session_id = session[0]
        user_email = session[1]
        login_time = session[2]
        logout_time = session[3]

        if login_time:
            created = login_time
            last_session_time = login_time
        else:
            created = ""
            last_session_time = ""

        if login_time:
            login_dt = datetime.strptime(login_time, "%Y-%m-%d %H:%M:%S")

            if logout_time:
                logout_dt = datetime.strptime(logout_time, "%Y-%m-%d %H:%M:%S")
            else:
                logout_dt = datetime.now()

            session_seconds = int((logout_dt - login_dt).total_seconds())
        else:
            session_seconds = 0

        cursor.execute("""
            SELECT COUNT(*)
            FROM ClickTracking
            WHERE SessionID = ?
        """, (
            session_id,
        ))

        event_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT PageName
            FROM ClickTracking
            WHERE SessionID = ?
            ORDER BY ClickID DESC
            LIMIT 1
        """, (
            session_id,
        ))

        last_page_row = cursor.fetchone()
        last_page = last_page_row[0] if last_page_row else ""

        name = user_email.split("@")[0] if user_email else ""

        export_rows.append((
            created,
            session_id,
            name,
            user_email,
            last_page,
            1,
            last_session_time,
            session_seconds,
            session_seconds,
            0,
            event_count,
            "",
            "",
            "",
            session_seconds,
            session_seconds,
            session_seconds,
            session_seconds,
            event_count,
            "",
            "",
            ""
        ))

    conn.close()

    return export_rows