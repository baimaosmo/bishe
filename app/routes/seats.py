from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Seat, SeatReservation
from app import db

seats_bp = Blueprint('seats', __name__)

def cleanup_expired_reservations():
    """
    逻辑核心：自动释放超时的座位 (3小时)
    """
    now = datetime.utcnow()
    expire_threshold = now - timedelta(hours=3)
    
    expired_records = SeatReservation.query.filter(
        SeatReservation.status == 'active',
        SeatReservation.start_time <= expire_threshold
    ).all()
    
    for record in expired_records:
        record.status = 'completed'
        record.end_time = now
        record.seat.status = 'free'
    
    if expired_records:
        db.session.commit()

# 1. 座位可视化大厅
@seats_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cleanup_expired_reservations()

    current_floor = request.args.get('floor', 1, type=int)
    
    active_reservation = SeatReservation.query.filter_by(
        user_id=session['user_id'], 
        status='active'
    ).first()

    remaining_minutes = None
    show_warning = False
    
    if active_reservation:
        used_delta = datetime.utcnow() - active_reservation.start_time
        used_minutes = used_delta.total_seconds() / 60
        remaining_minutes = int(max(0, 180 - used_minutes))
        
        if remaining_minutes <= 30:
            show_warning = True

    seats = Seat.query.filter_by(floor=current_floor).order_by(Seat.seat_number).all()
    areas = sorted(list(set([s.area for s in seats])))

    return render_template('seats/index.html', 
                         seats=seats, 
                         areas=areas,
                         current_floor=current_floor,
                         active_reservation=active_reservation,
                         remaining_minutes=remaining_minutes,
                         show_warning=show_warning)

# ================= 补回缺失的选座路由 =================
# 2. 选座请求处理
@seats_bp.route('/book/<int:seat_id>')
def book_seat(seat_id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    # 检查用户是否已经占了一个座位
    existing = SeatReservation.query.filter_by(user_id=session['user_id'], status='active').first()
    if existing:
        flash('您当前已经预约了一个座位，请先释放后再选新座！', 'error')
        return redirect(url_for('seats.index'))

    seat = Seat.query.get_or_404(seat_id)
    if seat.status != 'free':
        flash('手慢了，该座位已被抢占！', 'error')
        return redirect(url_for('seats.index'))

    try:
        # 创建预约记录并更新座位状态
        reservation = SeatReservation(user_id=session['user_id'], seat_id=seat.id)
        seat.status = 'occupied'
        
        db.session.add(reservation)
        db.session.commit()
        flash(f'选座成功！您的座位号是 {seat.seat_number}。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('选座失败，系统异常。', 'error')

    return redirect(url_for('seats.index'))
# ====================================================

# 3. 退座/释放请求处理
@seats_bp.route('/release/<int:reservation_id>')
def release_seat(reservation_id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    reservation = SeatReservation.query.get_or_404(reservation_id)
    
    if reservation.user_id != session['user_id'] and session.get('role') != 'admin':
        flash('无权操作！', 'error')
        return redirect(url_for('seats.index'))

    try:
        reservation.status = 'completed'
        reservation.end_time = datetime.utcnow()
        reservation.seat.status = 'free'
        
        db.session.commit()
        flash('座位已成功释放！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('释放失败，请稍后重试。', 'error')

    return redirect(url_for('seats.index'))