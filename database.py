import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config import get_settings

settings = get_settings()


def get_db_connection():
    """Tạo kết nối PostgreSQL"""
    conn = psycopg2.connect(
        settings.database_url,
        cursor_factory=RealDictCursor
    )
    return conn


@contextmanager
def get_db():
    """Context manager để quản lý kết nối database"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
