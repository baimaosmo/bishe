# =============================================================================
# app/__init__.py — Flask 应用工厂模块
# 负责: 创建 Flask 实例 → 加载配置 → 初始化插件 → 注册所有蓝图
# 使用工厂函数模式，便于测试和多环境部署
# =============================================================================

from flask import Flask  # Flask 核心类，用于创建 WSGI 应用
from flask_sqlalchemy import SQLAlchemy  # ORM 扩展，将数据库表映射为 Python 对象
from config import Config  # 导入项目配置类

# 1. 实例化 SQLAlchemy 对象（全局单例）
# 放在工厂函数外面是因为 models.py 也需要 import db 来定义模型类
# 这样做避免循环导入：models.py 导入 db，__init__.py 导入 models
db = SQLAlchemy()


def create_app(config_class=Config):
    """
    Flask 应用工厂函数
    参数: config_class — 配置类，默认使用 Config
    返回: 配置完成、蓝图已注册的 Flask 应用实例
    """

    # 2. 创建 Flask 核心对象
    app = Flask(__name__)

    # 3. 将 config.py 中的配置项加载到 app.config 字典中
    # 加载后可通过 app.config['SECRET_KEY'] 等方式访问
    app.config.from_object(config_class)

    # 4. 将 SQLAlchemy 与当前 Flask 应用绑定
    # init_app 使得 db 对象知道该连接哪个数据库
    db.init_app(app)

    # ------------------------------------------------------------------
    # 5. 注册蓝图 — 每个功能模块的路由都封装为独立的蓝图
    # 蓝图相当于 Flask 的"子应用"，可以把不同功能分到不同文件中
    # ------------------------------------------------------------------

    # 首页与数据看板蓝图（路由前缀: /）
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    # 用户认证蓝图（路由前缀: /auth）
    # 例如: /auth/login, /auth/register, /auth/logout
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # 图书管理蓝图（路由前缀: /books）
    # 例如: /books/list, /books/detail/1, /books/borrow/1
    from app.routes.books import books_bp
    app.register_blueprint(books_bp, url_prefix='/books')

    # 座位预约蓝图（路由前缀: /seats）
    # 例如: /seats/, /seats/book/1, /seats/release/1
    from app.routes.seats import seats_bp
    app.register_blueprint(seats_bp, url_prefix='/seats')

    # AI 智能工具蓝图（路由前缀: /ai）
    # 例如: /ai/smart-search, /ai/report
    from app.routes.ai_tools import ai_bp
    app.register_blueprint(ai_bp, url_prefix='/ai')

    # 图书漂流角蓝图（路由前缀: /crossing）
    # 例如: /crossing/, /crossing/publish, /crossing/detail/1
    from app.routes.book_crossing import crossing_bp
    app.register_blueprint(crossing_bp, url_prefix='/crossing')

    # 返回配置完成的 Flask 应用实例
    return app
