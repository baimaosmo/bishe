# =============================================================================
# run.py — 应用启动入口
# 负责: 创建 Flask 应用 → 检查/修复数据库结构 → 写入种子数据 → 启动服务器
# 启动命令: python run.py
# =============================================================================

from app import create_app, db  # 从 app 包导入工厂函数和数据库实例
from app.models import Publisher, Student, Teacher  # 导入出版社、学生、教师模型
from app.seed_data import seed_sample_data  # 导入种子数据填充函数
from sqlalchemy import inspect, text  # inspect 用于反射数据库结构，text 用于执行原生 SQL

# 1. 调用工厂函数创建 Flask 应用实例
# create_app() 会注册所有蓝图、加载配置、初始化插件
app = create_app()


def ensure_schema_compatibility():
    """
    数据库结构兼容性检查与自动修复函数
    如果数据库表缺少某些列（例如升级后新增的字段），自动执行 ALTER TABLE 补充列
    保证旧数据库升级到新版本代码时不会因列缺失而报错
    """
    # 获取数据库检查器，用于反射当前数据库中的表结构
    inspector = inspect(db.engine)

    # 检查 seat_reservations 表是否存在，存在则检查并补充缺失字段
    if 'seat_reservations' in inspector.get_table_names():
        # 获取 seat_reservations 表中所有列名
        columns = {column['name'] for column in inspector.get_columns('seat_reservations')}
        # 如果缺少 student_id 列，则添加（多账号体系需要）
        if 'student_id' not in columns:
            db.session.execute(text('ALTER TABLE seat_reservations ADD COLUMN student_id INT NULL'))
        # 如果已有 user_id 列，将其改为可空（兼容多账号设计）
        if 'user_id' in columns:
            db.session.execute(text('ALTER TABLE seat_reservations MODIFY COLUMN user_id INT NULL'))

    # 构建所有表的列名字典 {表名: {列名集合}}
    table_columns = {
        table: {column['name'] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }

    # 为 users 表补充 avatar（头像）列
    if 'users' in table_columns and 'avatar' not in table_columns['users']:
        db.session.execute(text('ALTER TABLE users ADD COLUMN avatar VARCHAR(255) NULL'))

    # 为 students 表补充 avatar 列
    if 'students' in table_columns and 'avatar' not in table_columns['students']:
        db.session.execute(text('ALTER TABLE students ADD COLUMN avatar VARCHAR(255) NULL'))

    # 为学生表和教师表补充 gender（性别）和 major（专业）列
    for table in ['students', 'teachers']:
        if table in table_columns:
            if 'gender' not in table_columns[table]:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN gender VARCHAR(10) NULL'))
            if 'major' not in table_columns[table]:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN major VARCHAR(80) NULL'))

    # 为借阅、预约、收藏、评价等业务表补充 teacher_id 列（支持教师账号）
    account_tables = ['borrow_records', 'seat_reservations', 'book_favorites', 'book_reviews']
    for table in account_tables:
        if table in table_columns and 'teacher_id' not in table_columns[table]:
            db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN teacher_id INT NULL'))

    # 为漂流图书相关表补充教师外键字段
    drift_columns = {
        'drift_books': ['provider_teacher_id', 'receiver_teacher_id'],  # 提供者/领取者教师外键
        'drift_requests': ['receiver_teacher_id'],  # 申请者教师外键
    }
    for table, columns in drift_columns.items():
        if table in table_columns:
            for column in columns:
                if column not in table_columns[table]:
                    db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} INT NULL'))

    # 提交所有 DDL（表结构修改）操作
    db.session.commit()


def seed_default_publishers_and_teacher():
    """
    写入默认出版社列表和一个示例教师账号
    只在数据为空时写入，已存在则跳过（幂等操作）
    """
    # 预置 6 个常见出版社，方便管理员添加图书时下拉选择
    default_publishers = [
        '人民邮电出版社', '机械工业出版社', '清华大学出版社',
        '电子工业出版社', '高等教育出版社', '人民文学出版社'
    ]
    for name in default_publishers:
        # 检查出版社是否已存在，避免重复插入
        if not Publisher.query.filter_by(name=name).first():
            db.session.add(Publisher(name=name))

    # 创建示例教师账号 T10001（如果不存在）
    if not Teacher.query.filter_by(job_no='T10001').first():
        teacher = Teacher(
            job_no='T10001',
            name='示例教师',
            gender='男',
            major='图书情报管理',
            department='图书情报管理'
        )
        teacher.set_password('Teacher@123')  # 调用模型方法对密码哈希
        db.session.add(teacher)

    # 修复旧数据：如果学生的 major 字段为空，用 department 字段值填充
    for student in Student.query.filter(Student.major.is_(None)).all():
        student.major = student.department

    db.session.commit()


# Python 脚本入口：直接运行 python run.py 时执行以下代码
if __name__ == '__main__':
    # 2. 推入应用上下文，使得 db.create_all() 等操作知道当前的 Flask 应用是哪个
    with app.app_context():
        # 自动创建所有模型对应的数据库表（已存在的表不会被重复创建）
        db.create_all()
        # 检查并修复数据库结构兼容性
        ensure_schema_compatibility()
        # 写入默认出版社和示例教师
        seed_default_publishers_and_teacher()
        # 写入全套种子数据（用户、图书、借阅记录、座位等）
        seed_sample_data()
        print("数据库表结构已检查完毕 (如果不存在则已自动创建)。")

    # 3. 启动 Flask 开发服务器
    # host='127.0.0.1' → 只允许本机访问（安全）；改为 0.0.0.0 可允许局域网访问
    # port=5000 → Flask 默认端口
    # debug=True → 开启调试模式：代码改动自动重启，浏览器显示详细错误堆栈
    app.run(host='127.0.0.1', port=5000, debug=True)
