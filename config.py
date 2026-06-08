import os  # 导入 os 模块，用于读取操作系统环境变量

class Config:
    """Flask 应用全局配置类，集中管理密钥、数据库连接和第三方 API 密钥"""

    # Flask 安全密钥，用于加密 Session 和 CSRF Token
    # 优先从环境变量读取（生产环境），其次使用默认值（开发环境）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-library-secret-key-2026'

    # MySQL 数据库连接 URI
    # 格式: mysql+pymysql://用户名:密码@主机地址:端口/数据库名?charset=utf8mb4
    # pymysql 是 Python 连接 MySQL 的驱动；charset=utf8mb4 支持 emoji 等四字节字符
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/library?charset=utf8mb4'

    # 关闭 SQLAlchemy 的信号追踪机制，节省内存开销
    # Flask-SQLAlchemy 默认会追踪对象修改并发送信号，此处关闭提升性能
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # DeepSeek 大模型 API 密钥，用于 AI 智能检索和报告生成功能
    DEEPSEEK_API_KEY = 'sk-a348e09846e74e9d8e5ed73f76c5299a'
