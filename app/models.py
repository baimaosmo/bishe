from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# 1. 注册用户表（校外读者/管理员）
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    email = db.Column(db.String(120), unique=True, comment='邮箱')
    password_hash = db.Column(db.String(255), nullable=False, comment='密码')
    role = db.Column(db.String(20), default='user', comment='角色: user/admin')
    avatar = db.Column(db.String(255), comment='头像路径')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. 导入学生表（校内学生） - 新增表！
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_no = db.Column(db.String(20), unique=True, nullable=False, comment='学号')
    name = db.Column(db.String(50), nullable=False, comment='真实姓名')
    department = db.Column(db.String(50), default='计算机学院', comment='院系')
    password_hash = db.Column(db.String(255), nullable=False, comment='密码')
    avatar = db.Column(db.String(255), comment='头像路径')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 3. 教师用户表（使用工号登录）
class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_no = db.Column(db.String(20), unique=True, nullable=False, comment='工号')
    name = db.Column(db.String(50), nullable=False, comment='姓名')
    department = db.Column(db.String(50), default='教务部门', comment='院系/部门')
    password_hash = db.Column(db.String(255), nullable=False, comment='密码')
    avatar = db.Column(db.String(255), comment='头像路径')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Publisher(db.Model):
    __tablename__ = 'publishers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False, comment='出版社名称')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def __repr__(self):
        return f'<Publisher {self.name}>'


# 4. 借阅记录表（核心升级：多账号外键设计）
class BorrowRecord(db.Model):
    __tablename__ = 'borrow_records'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # 既可以关联普通 User，也可以关联 Student (两个字段其中一个为空)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='关联注册用户')
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True, comment='关联导入学生')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True, comment='关联教师用户')
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, comment='关联图书')
    
    borrow_time = db.Column(db.DateTime, default=datetime.now, comment='借阅时间')
    return_time = db.Column(db.DateTime, nullable=True, comment='归还时间')
    status = db.Column(db.String(20), default='borrowing', comment='状态: borrowing/returned')

    # 建立关系，方便在前端调用 record.book.title 等
    user = db.relationship('User', backref=db.backref('borrow_records', lazy=True))
    student = db.relationship('Student', backref=db.backref('borrow_records', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('borrow_records', lazy=True))
    book = db.relationship('Book', backref=db.backref('borrow_records', lazy=True))

class Book(db.Model):
    """图书基础信息表"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False, comment='书名')
    author = db.Column(db.String(50), nullable=False, comment='作者')
    
    # ================= 补回出版社字段 =================
    publisher = db.Column(db.String(100), comment='出版社')
    # ==================================================
    
    isbn = db.Column(db.String(20), unique=True, nullable=False, comment='ISBN号')
    category = db.Column(db.String(50), comment='分类')
    
    # 馆藏位置信息
    floor = db.Column(db.Integer, default=1, comment='所在楼层')
    area = db.Column(db.String(20), default='A区', comment='所在区域')
    shelf = db.Column(db.String(20), default='01架', comment='书架号')

    status = db.Column(db.String(20), default='available', comment='状态: available(可借), borrowed(已借出)')
    description = db.Column(db.Text, comment='简介')
    cover_image = db.Column(db.String(255), comment='封面图片路径')
    add_time = db.Column(db.DateTime, default=datetime.now, comment='入库时间')

    def __repr__(self):
        return f'<Book {self.title}>'



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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    seat_id = db.Column(db.Integer, db.ForeignKey('seats.id'), nullable=False)

    start_time = db.Column(db.DateTime, default=datetime.utcnow, comment='入座时间')
    end_time = db.Column(db.DateTime, nullable=True, comment='离座时间')
    status = db.Column(db.String(20), default='active', comment='状态: active(使用中), completed(已结束)')

    user = db.relationship('User', backref=db.backref('seat_reservations', lazy=True))
    student = db.relationship('Student', backref=db.backref('seat_reservations', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('seat_reservations', lazy=True))
    seat = db.relationship('Seat', backref=db.backref('reservations', lazy=True))

    @property
    def account_name(self):
        if self.user:
            return self.user.username
        if self.student:
            return self.student.name
        if self.teacher:
            return self.teacher.name
        return '未知用户'

    def __repr__(self):
        return f'<SeatReservation Seat:{self.seat_id} Status:{self.status}>'

# ================= 新增：图书漂流角 =================
class DriftBook(db.Model):
    """漂流图书表"""
    __tablename__ = 'drift_books'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False, comment='书名')
    course_related = db.Column(db.String(100), comment='关联课程')
    condition = db.Column(db.String(20), default='良好', comment='新旧程度: 全新/良好/一般/较旧')
    description = db.Column(db.Text, comment='补充描述/交换条件')
    status = db.Column(db.String(20), default='drifting', comment='状态: drifting(漂流中)/claimed(已领走)')
    publish_time = db.Column(db.DateTime, default=datetime.now, comment='发布时间')

    # 提供者：双外键（User 或 Student）
    provider_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    provider_student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    provider_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    # 领取者：多账号外键
    receiver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    receiver_student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    receiver_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    provider_user = db.relationship('User', foreign_keys=[provider_user_id],
                                    backref=db.backref('drift_books_provided', lazy=True))
    provider_student = db.relationship('Student', foreign_keys=[provider_student_id],
                                       backref=db.backref('drift_books_provided', lazy=True))
    provider_teacher = db.relationship('Teacher', foreign_keys=[provider_teacher_id],
                                       backref=db.backref('drift_books_provided', lazy=True))
    receiver_user = db.relationship('User', foreign_keys=[receiver_user_id],
                                    backref=db.backref('drift_books_received', lazy=True))
    receiver_student = db.relationship('Student', foreign_keys=[receiver_student_id],
                                       backref=db.backref('drift_books_received', lazy=True))
    receiver_teacher = db.relationship('Teacher', foreign_keys=[receiver_teacher_id],
                                       backref=db.backref('drift_books_received', lazy=True))
    requests = db.relationship('DriftRequest', backref='book', lazy=True, cascade='all, delete-orphan')

    @property
    def provider_name(self):
        if self.provider_user:
            return self.provider_user.username
        if self.provider_student:
            return self.provider_student.name
        if self.provider_teacher:
            return self.provider_teacher.name
        return '未知'

    @property
    def receiver_name(self):
        if self.receiver_user:
            return self.receiver_user.username
        if self.receiver_student:
            return self.receiver_student.name
        if self.receiver_teacher:
            return self.receiver_teacher.name
        return None

    def __repr__(self):
        return f'<DriftBook {self.title}>'


class DriftRequest(db.Model):
    """漂流图书领取申请表"""
    __tablename__ = 'drift_requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    book_id = db.Column(db.Integer, db.ForeignKey('drift_books.id'), nullable=False)
    message = db.Column(db.Text, comment='给提供者的留言')
    status = db.Column(db.String(20), default='pending', comment='状态: pending(待确认)/accepted(已同意)/rejected(已拒绝)')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='申请时间')

    # 申请人：双外键
    receiver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    receiver_student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    receiver_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    receiver_user = db.relationship('User', foreign_keys=[receiver_user_id],
                                    backref=db.backref('drift_requests', lazy=True))
    receiver_student = db.relationship('Student', foreign_keys=[receiver_student_id],
                                       backref=db.backref('drift_requests', lazy=True))
    receiver_teacher = db.relationship('Teacher', foreign_keys=[receiver_teacher_id],
                                       backref=db.backref('drift_requests', lazy=True))

    @property
    def receiver_name(self):
        if self.receiver_user:
            return self.receiver_user.username
        if self.receiver_student:
            return self.receiver_student.name
        if self.receiver_teacher:
            return self.receiver_teacher.name
        return '未知'

    def __repr__(self):
        return f'<DriftRequest Book:{self.book_id} Status:{self.status}>'


class BookFavorite(db.Model):
    """图书收藏表"""
    __tablename__ = 'book_favorites'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    book = db.relationship('Book', backref=db.backref('favorites', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('book_favorites', lazy=True))
    student = db.relationship('Student', backref=db.backref('book_favorites', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('book_favorites', lazy=True))

    @property
    def account_name(self):
        if self.user:
            return self.user.username
        if self.student:
            return self.student.name
        if self.teacher:
            return self.teacher.name
        return '未知用户'


class BookReview(db.Model):
    """图书评价表"""
    __tablename__ = 'book_reviews'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False, default=5)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending', comment='pending/approved/rejected')
    created_at = db.Column(db.DateTime, default=datetime.now)

    book = db.relationship('Book', backref=db.backref('reviews', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('book_reviews', lazy=True))
    student = db.relationship('Student', backref=db.backref('book_reviews', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('book_reviews', lazy=True))

    @property
    def account_name(self):
        if self.user:
            return self.user.username
        if self.student:
            return self.student.name
        if self.teacher:
            return self.teacher.name
        return '未知用户'