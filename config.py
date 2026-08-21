"""Settings, stored as a single JSON file. No database anywhere in this project."""

import json
import os
import threading
from pathlib import Path

# Everything lives under one folder. Override with the FACESORT_DATA env var.
DATA_ROOT = Path(os.environ.get("FACESORT_DATA", Path.home() / "FaceSort")).expanduser()
EVENTS_DIR = DATA_ROOT / "events"
SETTINGS_FILE = DATA_ROOT / "settings.json"

DEFAULTS = {
    # auto | cpu | cuda | coreml
    "device": "auto",
    "model": "buffalo_l",
    # Detector input square. Bigger finds smaller faces but runs slower.
    "det_size": 640,
    # Long edge cap before detection. Protects memory on 45MP files.
    "max_image_side": 2200,
    # Faces narrower than this are ignored (back row of group shots).
    "min_face_px": 40,
    # Cosine similarity cut-off for "same person".
    "threshold": 0.42,
    # Keep face vectors after a run so re-matching is instant.
    "cache_embeddings": True,
    "thumb_size": 420,
    # Copy matched files, or hard-link them to save disk.
    "copy_mode": "copy",
    "admin_username": "admin",
    "admin_password": "admin123",
    "google_client_id": "",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
}

_lock = threading.Lock()
_cache = None


def ensure_dirs():
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)


def get_db_connection(create_db=True):
    import pymysql
    try:
        conn = pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password="password",
            charset="utf8mb4"
        )
        if create_db:
            with conn.cursor() as cursor:
                cursor.execute("CREATE DATABASE IF NOT EXISTS facesort CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
        conn.close()
        
        return pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password="password",
            database="facesort",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Error connecting to MySQL: {e}", flush=True)
        return None


def init_mysql_db():
    conn = get_db_connection(create_db=True)
    if not conn:
        print("Skipping MySQL initialization: DB connection failed.", flush=True)
        return
        
    try:
        with conn.cursor() as cursor:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username VARCHAR(80) PRIMARY KEY,
                    password_hash VARCHAR(256) NOT NULL,
                    name VARCHAR(150),
                    email VARCHAR(150),
                    mobile VARCHAR(50),
                    usertype VARCHAR(50) NOT NULL
                ) ENGINE=InnoDB;
            """)
            
            # Query column structure
            cursor.execute("DESCRIBE users")
            rows = cursor.fetchall()
            columns = {row["Field"] for row in rows}
            
            # Make any NOT NULL columns without default values nullable (except primary key)
            for r in rows:
                field = r["Field"]
                is_nullable = r["Null"] == "YES"
                default_val = r["Default"]
                key = r["Key"]
                if not is_nullable and default_val is None and field != "username" and key != "PRI":
                    field_type = r["Type"]
                    cursor.execute(f"ALTER TABLE users MODIFY COLUMN `{field}` {field_type} DEFAULT NULL;")
                    
            if "password_hash" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(256) NOT NULL;")
            if "name" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN name VARCHAR(150);")
            if "email" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(150);")
            if "mobile" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN mobile VARCHAR(50);")
            if "usertype" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN usertype VARCHAR(50) NOT NULL DEFAULT 'member';")
            else:
                cursor.execute("ALTER TABLE users MODIFY COLUMN usertype VARCHAR(50) NOT NULL DEFAULT 'member';")

            # Create settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    `key` VARCHAR(100) PRIMARY KEY,
                    `value` TEXT NOT NULL
                ) ENGINE=InnoDB;
            """)
            
            # Migrate existing local users to MySQL
            cursor.execute("SELECT username FROM users")
            db_usernames = {r["username"] for r in cursor.fetchall()}
            
            admin_user = DEFAULTS.get("admin_username", "admin")
            admin_pass = DEFAULTS.get("admin_password", "admin123")
            
            if admin_user not in db_usernames:
                local_users = {}
                users_file = DATA_ROOT / "users.json"
                if users_file.exists():
                    try:
                        local_users = json.loads(users_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                
                import hashlib
                def hash_pass(password: str) -> str:
                    return hashlib.sha256(password.encode("utf-8")).hexdigest()
                    
                if admin_user not in local_users:
                    local_users[admin_user] = {
                        "password_hash": hash_pass(admin_pass),
                        "name": "Super Admin",
                        "email": "admin@example.com",
                        "mobile": "",
                        "usertype": "super_admin"
                    }
                    
                for username, udata in local_users.items():
                    if username not in db_usernames:
                        if isinstance(udata, str):
                            p_hash = udata
                            name = "Super Admin" if username == admin_user else username
                            email = "admin@example.com" if username == admin_user else ""
                            mobile = ""
                            usertype = "super_admin" if username == admin_user else "member"
                        else:
                            p_hash = udata.get("password_hash")
                            name = udata.get("name", "")
                            email = udata.get("email", "")
                            mobile = udata.get("mobile", "")
                            usertype = udata.get("usertype", "member")
                            
                        cursor.execute("""
                            INSERT INTO users (username, password_hash, name, email, mobile, usertype)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (username, p_hash, name, email, mobile, usertype))
            
            # Migrate settings to MySQL
            cursor.execute("SELECT COUNT(*) as count FROM settings")
            row = cursor.fetchone()
            if row["count"] == 0:
                local_settings = dict(DEFAULTS)
                if SETTINGS_FILE.exists():
                    try:
                        local_settings.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
                    except Exception:
                        pass
                for k, v in local_settings.items():
                    cursor.execute("""
                        INSERT INTO settings (`key`, `value`)
                        VALUES (%s, %s)
                    """, (k, json.dumps(v)))
                    
        conn.commit()
        print("MySQL database and tables initialized successfully.", flush=True)
    except Exception as e:
        print(f"Error initializing MySQL database: {e}", flush=True)
    finally:
        conn.close()


init_mysql_db()


def load():
    global _cache
    with _lock:
        if _cache is not None:
            return dict(_cache)
        ensure_dirs()
        values = dict(DEFAULTS)
        
        # Load from MySQL
        conn = get_db_connection(create_db=False)
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW TABLES LIKE 'settings'")
                    if cursor.fetchone():
                        cursor.execute("SELECT `key`, `value` FROM settings")
                        rows = cursor.fetchall()
                        for row in rows:
                            key = row["key"]
                            val_str = row["value"]
                            try:
                                values[key] = json.loads(val_str)
                            except Exception:
                                values[key] = val_str
            except Exception as e:
                print(f"Error loading settings from MySQL: {e}", flush=True)
            finally:
                conn.close()
        _cache = values
        return dict(values)


def save(patch: dict):
    global _cache
    values = load()
    for key, value in patch.items():
        if key in DEFAULTS:
            values[key] = value
            
    conn = get_db_connection(create_db=False)
    if conn:
        try:
            with conn.cursor() as cursor:
                for key, value in patch.items():
                    if key in DEFAULTS:
                        val_str = json.dumps(value)
                        cursor.execute("""
                            INSERT INTO settings (`key`, `value`)
                            VALUES (%s, %s)
                            ON DUPLICATE KEY UPDATE `value` = %s
                        """, (key, val_str, val_str))
            conn.commit()
        except Exception as e:
            print(f"Error saving settings to MySQL: {e}", flush=True)
        finally:
            conn.close()
            
    with _lock:
        _cache = values
    return dict(values)


def get(key):
    return load()[key]
