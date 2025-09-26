# logger.py
import logging
import os
from datetime import datetime

def setup_logger(name, log_path='logs'):
    """
    设置一个带有文件和控制台输出的logger
    
    Args:
        name (str): logger的名称
        log_path (str): 日志文件存放的目录
        
    Returns:
        logging.Logger: 配置好的logger对象
    """
    # 创建日志目录
    if not os.path.exists(log_path):
        os.makedirs(log_path)
        
    # 创建logger对象
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器 - 每天一个日志文件
    today = datetime.now().strftime('%Y-%m-%d')
    file_handler = logging.FileHandler(
        os.path.join(log_path, f'{name}_{today}.log'),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 创建默认logger
default_logger = setup_logger('info_fusion')