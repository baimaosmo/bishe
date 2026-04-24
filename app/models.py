from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """用户表模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True, comment='用户名')
    password_hash = db.Column(db.String(255), nullable=False, comment='加密后的密码')
    role = db.Column(db.String(20), default='user', comment='角色: admin(管理员), user(普通用户)')
    register_time = db.Column(db.DateTime, default=datetime.utcnow, comment='注册时间')

    def set_password(self, password):
        """将明文密码加密后存入 password_hash"""
        # 显式指定使用 pbkdf2:sha256 加密方式，解决 Anaconda 环境下 scrypt 报错的问题
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Book(db.Model):
    """图书信息表模型"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isbn = db.Column(db.String(20), unique=True, index=True, nullable=False, comment='国际标准书号')
    title = db.Column(db.String(100), nullable=False, comment='书名')
    author = db.Column(db.String(50), comment='作者')
    publisher = db.Column(db.String(50), comment='出版社')
    category = db.Column(db.String(30), comment='分类')
    status = db.Column(db.String(20), default='available', comment='状态: available(可借), borrowed(已借出)')
    add_time = db.Column(db.DateTime, default=datetime.utcnow, comment='入库时间')

    def __repr__(self):
        return f'<Book {self.title}>'

# ================= 新增：借阅记录表 =================
class BorrowRecord(db.Model):
    """借阅记录表模型 (关联 User 和 Book)"""
    __tablename__ = 'borrow_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 外键关联到 users 表的 id
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='借阅用户的ID')
    # 外键关联到 books 表的 id
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, comment='借阅图书的ID')
    
    borrow_time = db.Column(db.DateTime, default=datetime.utcnow, comment='借出时间')
    return_time = db.Column(db.DateTime, nullable=True, comment='实际归还时间')
    
    status = db.Column(db.String(20), default='borrowing', comment='状态: borrowing(借阅中), returned(已归还)')

    # 设置反向引用关系，方便通过 user.borrow_records 直接查询用户的借阅历史
    user = db.relationship('User', backref=db.backref('borrow_records', lazy=True))
    book = db.relationship('Book', backref=db.backref('borrow_records', lazy=True))

  # ================= 新增：座位管理表 =================
class Seat(db.Model):
    """座位基础信息表"""
    __tablename__ = 'seats'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    floor = db.Column(db.Integer, nullable=False, default=1, comment='楼层') # 新增：楼层
    area = db.Column(db.String(50), nullable=False, comment='所属区域')
    seat_number = db.Column(db.String(20), unique=True, nullable=False, comment='座位号')
    has_power = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='free') # free, occupied

    def __repr__(self):
        return f'<Seat {self.floor}F-{self.area}-{self.seat_number}>'
class SeatReservation(db.Model):
    """座位预约记录表"""
    __tablename__ = 'seat_reservations'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey('seats.id'), nullable=False)
    
    start_time = db.Column(db.DateTime, default=datetime.utcnow, comment='入座时间')
    end_time = db.Column(db.DateTime, nullable=True, comment='离座时间')
    status = db.Column(db.String(20), default='active', comment='状态: active(使用中), completed(已结束)')

    # 反向引用
    user = db.relationship('User', backref=db.backref('seat_reservations', lazy=True))
    seat = db.relationship('Seat', backref=db.backref('reservations', lazy=True))

    def __repr__(self):
        return f'<SeatReservation User:{self.user_id} Seat:{self.seat_id}>'