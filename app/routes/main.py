# =============================================================================
# app/routes/main.py — 首页与数据看板路由
# 负责: 系统首页 Dashboard，展示核心统计数据与最近活动动态
# 蓝图名: main_bp，挂载在根路径 /
# =============================================================================

from datetime import datetime  # 用于获取当天日期，统计今日借阅量
from flask import Blueprint, render_template, redirect, url_for, session  # Flask 核心工具
from sqlalchemy import func  # SQL 函数，用于 COUNT 等聚合查询
from app.models import Book, BorrowRecord, Seat, SeatReservation  # 需要的模型类

# 创建首页蓝图实例，'main' 是蓝图名称，__name__ 是当前模块名
main_bp = Blueprint('main', __name__)

# 路由: GET / → 系统首页 Dashboard
@main_bp.route('/')
def dashboard():
    """
    首页数据看板
    展示: 馆藏总数、今日借阅量、空闲座位数、最近借阅/预约动态
    """

    # 未登录用户跳转到登录页面
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取今天的日期对象
    today = datetime.now().date()

    # 统计今日借阅数量 — 条件: borrow_time 的日期部分等于今天
    borrowed_today = BorrowRecord.query.filter(
        func.date(BorrowRecord.borrow_time) == today  # func.date() 提取 DATETIME 的日期部分
    ).count()

    # 统计空闲座位数
    free_seats = Seat.query.filter_by(status='free').count()

    # 统计座位总数
    total_seats = Seat.query.count()

    # 组装统计数据字典，传给前端模板
    system_stats = {
        'total_books': Book.query.count(),  # 馆藏总数
        'borrowed_today': borrowed_today,   # 今日借阅
        'free_seats': free_seats,           # 空闲座位
        'total_seats': total_seats,         # 座位总数
        'ai_calls': BorrowRecord.query.count()  # 累计借阅次数（反映系统活跃度）
    }

    # 获取最近 6 条借阅记录，按借阅时间倒序
    recent_records = BorrowRecord.query.order_by(BorrowRecord.borrow_time.desc()).limit(6).all()

    # 获取最近 4 条座位预约记录
    recent_reservations = SeatReservation.query.order_by(SeatReservation.start_time.desc()).limit(4).all()

    # 组装"最近动态"列表，将借阅和预约统一格式后合并
    recent_activities = []

    # 遍历借阅记录，提取显示信息
    for record in recent_records:
        # 根据记录中外键非空情况确定用户名（三选一）
        if record.student:
            name = record.student.name
        elif record.teacher:
            name = record.teacher.name
        elif record.user:
            name = record.user.username
        else:
            name = '未知用户'

        # 根据记录状态确定动作文本
        action = '归还了' if record.status == 'returned' else '借阅了'

        # 添加到活动列表
        recent_activities.append({
            'user': name,
            'action': action,
            'item': f'《{record.book.title}》',  # 书名用书名号包裹
            'time': record.borrow_time.strftime('%Y-%m-%d %H:%M')  # 格式化时间
        })

    # 遍历座位预约记录
    for reservation in recent_reservations:
        recent_activities.append({
            'user': reservation.account_name,  # 使用模型的计算属性获取用户名
            'action': '预约了',
            'item': f'{reservation.seat.seat_number} 座位',
            'time': reservation.start_time.strftime('%Y-%m-%d %H:%M')
        })

    # 按时间倒序排列所有活动，取前 8 条
    recent_activities = sorted(recent_activities, key=lambda item: item['time'], reverse=True)[:8]

    # 渲染 dashboard.html 模板，将统计数据与活动列表传入
    return render_template(
        'dashboard.html',
        stats=system_stats,
        activities=recent_activities
    )
