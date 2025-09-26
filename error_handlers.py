# error_handlers.py
import functools
import traceback
from logger import default_logger

def handle_errors(func):
    """
    装饰器：统一处理函数异常，记录错误日志
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error in {func.__name__}: {str(e)}\n{traceback.format_exc()}"
            default_logger.error(error_msg)
            raise
    return wrapper