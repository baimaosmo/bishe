import os

class Config:
    # Flask 安全密钥（用于保证 Session 和表单的安全性）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-library-secret-key-2026'
    
    # MySQL 数据库配置 
    # 格式规范: mysql+pymysql://用户名:密码@主机地址:端口/数据库名
    # 注意：运行前请确保你在本地 MySQL 中已经执行了 CREATE DATABASE smart_library_db;
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/library?charset=utf8mb4'
    
    # 关闭 SQLAlchemy 对模型修改的事件追踪，以节省系统内存
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEEPSEEK_API_KEY = 'sk-a348e09846e74e9d8e5ed73f76c5299a'                                              