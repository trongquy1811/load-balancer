import hashlib
from typing import Dict, Any, Optional
from database.db import get_db_connection
from utils.logger import logger

class AuthManager:
    """Quản lý đăng ký, đăng nhập và phân quyền người dùng."""
    
    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @classmethod
    def register_user(cls, username: str, password: str, role: str = "User") -> bool:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            pwd_hash = cls._hash_password(password)
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                           (username, pwd_hash, role))
            conn.commit()
            conn.close()
            logger.info(f"Đã đăng ký tài khoản mới: {username} ({role})")
            return True
        except Exception as e:
            logger.error(f"Lỗi đăng ký người dùng {username}: {e}")
            return False

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        pwd_hash = cls._hash_password(password)
        cursor.execute("SELECT username, role FROM users WHERE username = ? AND password_hash = ?", 
                       (username, pwd_hash))
        row = cursor.fetchone()
        conn.close()
        if row:
            logger.info(f"Người dùng {username} đăng nhập thành công.")
            return {"username": row["username"], "role": row["role"]}
        logger.warning(f"Đăng nhập thất bại cho username: {username}")
        return None
