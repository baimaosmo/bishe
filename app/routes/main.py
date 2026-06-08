from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session
from sqlalchemy import func
from app.models import Book, BorrowRecord, Seat, SeatReservation

# 创建首页蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    # 未登录用户跳转到登录页
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    today = datetime.now().date()
    borrowed_today = BorrowRecord.query.filter(
        func.date(BorrowRecord.borrow_time) == today
    ).count()
    free_seats = Seat.query.filter_by(status='free').count()
    total_seats = Seat.query.count()

    system_stats = {
        'total_books': Book.query.count(),
        'borrowed_today': borrowed_today,
        'free_seats': free_seats,
        'total_seats': total_seats,
        'ai_calls': BorrowRecord.query.count()
    }

    recent_records = BorrowRecord.query.order_by(BorrowRecord.borrow_time.desc()).limit(6).all()
    recent_reservations = SeatReservation.query.order_by(SeatReservation.start_time.desc()).limit(4).all()
    recent_activities = []

    for record in recent_records:
        name = record.user.username if record.user else (record.student.name if record.student else '未知用户')
        action = '归还了' if record.status == 'returned' else '借阅了'
        recent_activities.append({
            'user': name,
            'action': action,
            'item': f'《{record.book.title}》',
            'time': record.borrow_time.strftime('%Y-%m-%d %H:%M')
        })

    for reservation in recent_reservations:
        recent_activities.append({
            'user': reservation.account_name,
            'action': '预约了',
            'item': f'{reservation.seat.seat_number} 座位',
            'time': reservation.start_time.strftime('%Y-%m-%d %H:%M')
        })

    recent_activities = sorted(recent_activities, key=lambda item: item['time'], reverse=True)[:8]

    # 将数据传递给前端模板
    return render_template(
        'dashboard.html',
        stats=system_stats,
        activities=recent_activities
    )