from flask import Blueprint, render_template

# 创建首页蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    # 这里准备传给前端的动态数据。
    # 后期这里会替换为 sqlalchemy 的查询语句，例如：Book.query.count()
    system_stats = {
        'total_books': 24592,       # 馆藏总数
        'borrowed_today': 128,      # 今日借出
        'free_seats': 86,           # 空闲座位
        'total_seats': 200,         # 总座位数
        'ai_calls': 3402            # AI调用次数
    }
    
    # 近期动态模拟数据
    recent_activities = [
        {"user": "张三", "action": "借阅了", "item": "《Flask Web开发实战》", "time": "10分钟前"},
        {"user": "李四", "action": "归还了", "item": "《软件工程导论》", "time": "半小时前"},
        {"user": "王五", "action": "预约了", "item": "A区 032号座位", "time": "1小时前"}
    ]

    # 将数据传递给前端模板
    return render_template(
        'dashboard.html', 
        stats=system_stats, 
        activities=recent_activities
    )