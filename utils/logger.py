import os
import logging
from config import Config

def setup_logger(name: str = "CloudSystem") -> logging.Logger:
    """Khởi tạo và trả về Logger đa kênh ghi log hệ thống, request và lỗi."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Console Handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File Handler cho System Logs
        sys_log_path = os.path.join(Config.LOG_DIR, "system.log")
        fh_sys = logging.FileHandler(sys_log_path, encoding='utf-8')
        fh_sys.setFormatter(formatter)
        logger.addHandler(fh_sys)

        # File Handler riêng cho Error Logs
        err_log_path = os.path.join(Config.LOG_DIR, "error.log")
        fh_err = logging.FileHandler(err_log_path, encoding='utf-8')
        fh_err.setLevel(logging.ERROR)
        fh_err.setFormatter(formatter)
        logger.addHandler(fh_err)

    return logger

logger = setup_logger()
