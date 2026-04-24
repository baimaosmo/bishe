from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# 1. 实例化 SQLAlchemy
# 放在工厂函数外面是为了让 models.py 能够引用它而不产生循环导入
db = SQLAlchemy()

def create_app(config_class=Config):
    """
    Flask 应用工厂函数
    """
    app = Flask(__name__)
    
    # 2. 加载 config.py 中的配置（包含数据库连接字符串等）
    app.config.from_object(config_class)

    # 3. 将 SQLAlchemy 插件绑定到当前的 app 实例
    db.init_app(app)

    # -----------------------------------------------------------
    # 4. 注册蓝图 (Blueprints)
    # 每一个新开发的功能模块路由文件，都必须在这里注册后才能被访问
    # -----------------------------------------------------------
    
    # 首页与基础数据看板模块 (对应的 URL 路径为 /)
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    # 用户认证模块 (对应的 URL 路径前缀为 /auth，例如 /auth/login)
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # 图书管理模块 (对应的 URL 路径前缀为 /books)
    from app.routes.books import books_bp
    app.register_blueprint(books_bp, url_prefix='/books')
    #选座模块
    from app.routes.seats import seats_bp
    app.register_blueprint(seats_bp, url_prefix='/seats')

    # AI 智能工具模块 (对应的 URL 路径前缀为 /ai)
    # from app.routes.ai_tools import ai_bp
    # app.register_blueprint(ai_bp, url_prefix='/ai')
    from app.routes.ai_tools import ai_bp
    app.register_blueprint(ai_bp, url_prefix='/ai')

    return app