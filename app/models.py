# =============================================================================
# app/models.py — 数据库模型定义层（ORM 映射）
# 使用 SQLAlchemy ORM 将 MySQL 数据库表映射为 Python 类
# 每个类对应一张数据库表，类的属性对应表中的列
# 所有业务数据（用户、图书、借阅、座位、漂流、评价等）都在此定义
# =============================================================================

from app import db  # 导入在 __init__.py 中创建的 SQLAlchemy 实例
from datetime import datetime  # 用于记录创建时间等时间戳字段
from werkzeug.security import generate_password_hash, check_password_hash  # 密码哈希与校验


# ==================== 1. 注册用户表（普通读者 / 管理员） ====================
class User(db.Model):
    """
    普通注册用户表 — 存放校外读者和系统管理员
    登录方式: 用户名 + 密码
    """
    __tablename__ = 'users'  # 指定数据库中的表名

    # 主键，自增整数 ID
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 用户名，唯一且不为空，用于登录
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    # 邮箱，可选且唯一
    email = db.Column(db.String(120), unique=True, comment='邮箱')
    # 密码哈希值（不存明文密码）
    password_hash = db.Column(db.String(255), nullable=False, comment='密码')
    # 角色：user（普通用户）或 admin（管理员）
    role = db.Column(db.String(20), default='user', comment='角色: user/admin')
    # 头像图片路径（相对于 static 目录）
    avatar = db.Column(db.String(255), comment='头像路径')

    def set_password(self, password):
        """将明文密码进行哈希加密后存入 password_hash 字段"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """校验用户输入的明文密码是否与数据库中的哈希值匹配"""
        return check_password_hash(self.password_hash, password)


# ==================== 2. 学生用户表（校内学生） ====================
class Student(db.Model):
    """
    学生用户表 — 存放通过批量导入或自主注册的校内学生账号
    登录方式: 学号 + 密码
    """
    __tablename__ = 'students'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 学号，唯一标识学生身份，用于登录
    student_no = db.Column(db.String(20), unique=True, nullable=False, comment='学号')
    # 学生真实姓名，页面显示用
    name = db.Column(db.String(50), nullable=False, comment='真实姓名')
    # 性别
    gender = db.Column(db.String(10), comment='性别')
    # 专业
    major = db.Column(db.String(80), comment='专业')
    # 院系，默认"计算机学院"
    department = db.Column(db.String(50), default='计算机学院', comment='院系/专业')
    # 密码哈希
    password_hash = db.Column(db.String(255), nullable=False, comment='密码')
    # 头像路径
    avatar = db.Column(db.String(255), comment='头像路径')

    def set_password(self, password):
        """密码哈希存储"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证明文密码"""
        return check_password_hash(self.password_hash, password)


# ==================== 3. 教师用户表 ====================
class Teacher(db.Model):
    """
    教师用户表 — 存放校内教师账号
    登录方式: 工号 + 密码
    """
    __tablename__ = 'teachers'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 工号，唯一标识教师身份，用于登录
    job_no = db.Column(db.String(20), unique=True, nullable=False, comment='工号')
    # 教师姓名
    name = db.Column(db.String(50), nullable=False, comment='姓名')
    # 性别
    gender = db.Column(db.String(10), comment='性别')
    # 专业/研究方向
    major = db.Column(db.String(80), comment='专业/研究方向')
    # 院系/部门
    department = db.Column(db.String(50), default='教务部门', comment='院系/部门')
    # 密码哈希
    password_hash = db.Column(db.String(255), nullable=False, comment='密码')
    # 头像路径
    avatar = db.Column(db.String(255), comment='头像路径')

    def set_password(self, password):
        """密码哈希存储"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证明文密码"""
        return check_password_hash(self.password_hash, password)


# ==================== 4. 出版社表 ====================
class Publisher(db.Model):
    """
    出版社字典表 — 存储出版社名称
    管理员添加/编辑图书时可从已有出版社中下拉选择
    """
    __tablename__ = 'publishers'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 出版社名称，唯一
    name = db.Column(db.String(100), unique=True, nullable=False, comment='出版社名称')
    # 创建时间
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def __repr__(self):
        """调试打印时的友好显示"""
        return f'<Publisher {self.name}>'


# ==================== 5. 借阅记录表 ====================
class BorrowRecord(db.Model):
    """
    借阅记录表 — 记录每一次图书借出和归还操作
    支持三种账号类型: 普通用户(user)、学生(student)、教师(teacher)
    通过三个可为空的外键字段实现多态关联
    """
    __tablename__ = 'borrow_records'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 三个外键字段分别对应三张用户表，每次借阅只有一个非空
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='关联注册用户')
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True, comment='关联导入学生')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True, comment='关联教师用户')

    # 关联图书的外键，不允许为空
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, comment='关联图书')

    # 借阅时间，默认为当前时间
    borrow_time = db.Column(db.DateTime, default=datetime.now, comment='借阅时间')
    # 归还时间，归还前为空
    return_time = db.Column(db.DateTime, nullable=True, comment='归还时间')
    # 状态: borrowing（借阅中）或 returned（已归还）
    status = db.Column(db.String(20), default='borrowing', comment='状态: borrowing/returned')

    # 建立 ORM 关系，方便在代码中通过 record.user / record.book 直接访问关联对象
    # backref 表示反向引用，例如可通过 user.borrow_records 获取该用户所有借阅记录
    user = db.relationship('User', backref=db.backref('borrow_records', lazy=True))
    student = db.relationship('Student', backref=db.backref('borrow_records', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('borrow_records', lazy=True))
    book = db.relationship('Book', backref=db.backref('borrow_records', lazy=True))


# ==================== 6. 图书信息表 ====================
class Book(db.Model):
    """
    图书基础信息表 — 存储馆藏图书的所有元数据
    包含书名、作者、ISBN、分类、馆藏位置、借阅状态、封面图片等
    """
    __tablename__ = 'books'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 书名，必填，最长 100 字符
    title = db.Column(db.String(100), nullable=False, comment='书名')
    # 作者，必填
    author = db.Column(db.String(50), nullable=False, comment='作者')
    # 出版社
    publisher = db.Column(db.String(100), comment='出版社')
    # ISBN 号，唯一且必填，用于图书去重
    isbn = db.Column(db.String(20), unique=True, nullable=False, comment='ISBN号')
    # 图书分类（如"计算机"、"文学"、"人工智能"等）
    category = db.Column(db.String(50), comment='分类')

    # 馆藏位置 — 三个字段定位图书在图书馆中的物理位置
    floor = db.Column(db.Integer, default=1, comment='所在楼层')
    area = db.Column(db.String(20), default='A区', comment='所在区域')
    shelf = db.Column(db.String(20), default='01架', comment='书架号')

    # 借阅状态: available（可借）、borrowed（已借出）
    status = db.Column(db.String(20), default='available', comment='状态: available(可借), borrowed(已借出)')
    # 图书简介，TEXT 类型存储长文本
    description = db.Column(db.Text, comment='简介')
    # 封面图片路径
    cover_image = db.Column(db.String(255), comment='封面图片路径')
    # 入库时间
    add_time = db.Column(db.DateTime, default=datetime.now, comment='入库时间')

    def __repr__(self):
        """调试打印"""
        return f'<Book {self.title}>'


# ==================== 7. 座位管理表 ====================
class Seat(db.Model):
    """
    座位基础信息表 — 存储图书馆中每一个自习座位的属性
    支持多楼层、多区域的座位布局
    """
    __tablename__ = 'seats'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 所在楼层（1F、2F、3F...）
    floor = db.Column(db.Integer, nullable=False, default=1, comment='楼层')
    # 所属区域名称（如 A区、静音区、研讨间等）
    area = db.Column(db.String(50), nullable=False, comment='所属区域')
    # 座位号，唯一标识（如 1F-A-01）
    seat_number = db.Column(db.String(20), unique=True, nullable=False, comment='座位号')
    # 是否有电源插座
    has_power = db.Column(db.Boolean, default=False)
    # 座位状态: free（空闲）、occupied（已占用）
    status = db.Column(db.String(20), default='free')

    def __repr__(self):
        """调试打印: 楼层-区域-座位号"""
        return f'<Seat {self.floor}F-{self.area}-{self.seat_number}>'


# ==================== 8. 座位预约记录表 ====================
class SeatReservation(db.Model):
    """
    座位预约记录表 — 记录每一次座位预约和释放操作
    同样支持三种账号类型（user/student/teacher）
    """
    __tablename__ = 'seat_reservations'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 三个外键对应三张用户表（多态关联）
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    # 关联的座位外键
    seat_id = db.Column(db.Integer, db.ForeignKey('seats.id'), nullable=False)

    # 入座时间
    start_time = db.Column(db.DateTime, default=datetime.utcnow, comment='入座时间')
    # 离座时间（释放后才写入）
    end_time = db.Column(db.DateTime, nullable=True, comment='离座时间')
    # 状态: active（使用中）、completed（已结束）
    status = db.Column(db.String(20), default='active', comment='状态: active(使用中), completed(已结束)')

    # ORM 关系映射
    user = db.relationship('User', backref=db.backref('seat_reservations', lazy=True))
    student = db.relationship('Student', backref=db.backref('seat_reservations', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('seat_reservations', lazy=True))
    seat = db.relationship('Seat', backref=db.backref('reservations', lazy=True))

    @property
    def account_name(self):
        """
        计算属性 — 根据非空的外键自动判断预约者类型并返回显示名称
        不需要在数据库中存储，是动态计算的
        """
        if self.user:
            return self.user.username
        if self.student:
            return self.student.name
        if self.teacher:
            return self.teacher.name
        return '未知用户'

    def __repr__(self):
        return f'<SeatReservation Seat:{self.seat_id} Status:{self.status}>'


# ==================== 9. 漂流图书表 ====================
class DriftBook(db.Model):
    """
    漂流图书表 — 存储用户发布的共享/交换图书信息
    提供者可以是三种账号类型中的任意一种；
    领取者信息在申请被接受后写入对应外键字段
    """
    __tablename__ = 'drift_books'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 书名
    title = db.Column(db.String(100), nullable=False, comment='书名')
    # 关联课程（如"高等数学"、"数据结构"）
    course_related = db.Column(db.String(100), comment='关联课程')
    # 新旧程度: 全新、良好、一般、较旧
    condition = db.Column(db.String(20), default='良好', comment='新旧程度: 全新/良好/一般/较旧')
    # 补充描述或交换条件
    description = db.Column(db.Text, comment='补充描述/交换条件')
    # 状态: drifting（漂流中/可领取）、claimed（已被领走）
    status = db.Column(db.String(20), default='drifting', comment='状态: drifting(漂流中)/claimed(已领走)')
    # 发布时间
    publish_time = db.Column(db.DateTime, default=datetime.now, comment='发布时间')

    # 提供者外键（三选一非空）
    provider_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    provider_student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    provider_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    # 领取者外键（三选一非空，领取后写入）
    receiver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    receiver_student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    receiver_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    # ORM 关系映射 — 提供者
    provider_user = db.relationship('User', foreign_keys=[provider_user_id],
                                    backref=db.backref('drift_books_provided', lazy=True))
    provider_student = db.relationship('Student', foreign_keys=[provider_student_id],
                                       backref=db.backref('drift_books_provided', lazy=True))
    provider_teacher = db.relationship('Teacher', foreign_keys=[provider_teacher_id],
                                       backref=db.backref('drift_books_provided', lazy=True))

    # ORM 关系映射 — 领取者
    receiver_user = db.relationship('User', foreign_keys=[receiver_user_id],
                                    backref=db.backref('drift_books_received', lazy=True))
    receiver_student = db.relationship('Student', foreign_keys=[receiver_student_id],
                                       backref=db.backref('drift_books_received', lazy=True))
    receiver_teacher = db.relationship('Teacher', foreign_keys=[receiver_teacher_id],
                                       backref=db.backref('drift_books_received', lazy=True))

    # 关联的申请记录（级联删除：删除漂流图书时自动删除所有相关申请）
    requests = db.relationship('DriftRequest', backref='book', lazy=True, cascade='all, delete-orphan')

    @property
    def provider_name(self):
        """计算属性 — 返回提供者的显示名称"""
        if self.provider_user:
            return self.provider_user.username
        if self.provider_student:
            return self.provider_student.name
        if self.provider_teacher:
            return self.provider_teacher.name
        return '未知'

    @property
    def receiver_name(self):
        """计算属性 — 返回领取者的显示名称"""
        if self.receiver_user:
            return self.receiver_user.username
        if self.receiver_student:
            return self.receiver_student.name
        if self.receiver_teacher:
            return self.receiver_teacher.name
        return None

    def __repr__(self):
        return f'<DriftBook {self.title}>'


# ==================== 10. 漂流图书领取申请表 ====================
class DriftRequest(db.Model):
    """
    漂流图书领取申请表 — 记录用户对漂流图书的领取请求
    一条漂流图书可以由多人申请，但只有一条会被接受
    """
    __tablename__ = 'drift_requests'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 关联的漂流图书外键
    book_id = db.Column(db.Integer, db.ForeignKey('drift_books.id'), nullable=False)
    # 申请人留言（给提供者的话）
    message = db.Column(db.Text, comment='给提供者的留言')
    # 状态: pending（待确认）、accepted（已同意）、rejected（已拒绝）
    status = db.Column(db.String(20), default='pending', comment='状态: pending(待确认)/accepted(已同意)/rejected(已拒绝)')
    # 申请时间
    create_time = db.Column(db.DateTime, default=datetime.now, comment='申请时间')

    # 申请者外键（三选一）
    receiver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    receiver_student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    receiver_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    # ORM 关系
    receiver_user = db.relationship('User', foreign_keys=[receiver_user_id],
                                    backref=db.backref('drift_requests', lazy=True))
    receiver_student = db.relationship('Student', foreign_keys=[receiver_student_id],
                                       backref=db.backref('drift_requests', lazy=True))
    receiver_teacher = db.relationship('Teacher', foreign_keys=[receiver_teacher_id],
                                       backref=db.backref('drift_requests', lazy=True))

    @property
    def receiver_name(self):
        """计算属性 — 返回申请者的显示名称"""
        if self.receiver_user:
            return self.receiver_user.username
        if self.receiver_student:
            return self.receiver_student.name
        if self.receiver_teacher:
            return self.receiver_teacher.name
        return '未知'

    def __repr__(self):
        return f'<DriftRequest Book:{self.book_id} Status:{self.status}>'


# ==================== 11. 图书收藏表 ====================
class BookFavorite(db.Model):
    """
    图书收藏表 — 记录用户收藏了哪些图书
    用于"我的收藏"页面展示和推荐算法中偏好的计算
    """
    __tablename__ = 'book_favorites'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 被收藏的图书外键
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    # 收藏者外键（三选一）
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    # 收藏时间
    created_at = db.Column(db.DateTime, default=datetime.now)

    # ORM 关系 — 级联删除：删除图书时自动删除收藏记录
    book = db.relationship('Book', backref=db.backref('favorites', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('book_favorites', lazy=True))
    student = db.relationship('Student', backref=db.backref('book_favorites', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('book_favorites', lazy=True))

    @property
    def account_name(self):
        """计算属性 — 返回收藏者的显示名称"""
        if self.user:
            return self.user.username
        if self.student:
            return self.student.name
        if self.teacher:
            return self.teacher.name
        return '未知用户'


# ==================== 12. 图书评价表 ====================
class BookReview(db.Model):
    """
    图书评价表 — 存储用户对图书的评分和文字评价
    评价提交后默认状态为 pending，需经 AI 审核
    审核通过(approved)后才能在图书详情页公开展示
    """
    __tablename__ = 'book_reviews'

    # 主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 被评价的图书外键
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    # 评价者外键（三选一）
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    # 评分（1~5 星）
    rating = db.Column(db.Integer, nullable=False, default=5)
    # 评价文本内容
    content = db.Column(db.Text, nullable=False)
    # 审核状态: pending（待审核）、approved（已通过）、rejected（已驳回）
    status = db.Column(db.String(20), default='pending', comment='pending/approved/rejected')
    # 评价创建时间
    created_at = db.Column(db.DateTime, default=datetime.now)

    # ORM 关系 — 级联删除：删除图书时自动删除相关评价
    book = db.relationship('Book', backref=db.backref('reviews', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('book_reviews', lazy=True))
    student = db.relationship('Student', backref=db.backref('book_reviews', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('book_reviews', lazy=True))

    @property
    def account_name(self):
        """计算属性 — 返回评价者的显示名称"""
        if self.user:
            return self.user.username
        if self.student:
            return self.student.name
        if self.teacher:
            return self.teacher.name
        return '未知用户'
