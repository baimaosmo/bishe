from app import create_app, db
from app.models import Publisher, Teacher
from sqlalchemy import inspect, text

# 1. 调用工厂函数，创建 Flask 应用实例
app = create_app()


def ensure_schema_compatibility():
    inspector = inspect(db.engine)
    if 'seat_reservations' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('seat_reservations')}
        if 'student_id' not in columns:
            db.session.execute(text('ALTER TABLE seat_reservations ADD COLUMN student_id INT NULL'))
        if 'user_id' in columns:
            db.session.execute(text('ALTER TABLE seat_reservations MODIFY COLUMN user_id INT NULL'))

    table_columns = {
        table: {column['name'] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }
    if 'users' in table_columns and 'avatar' not in table_columns['users']:
        db.session.execute(text('ALTER TABLE users ADD COLUMN avatar VARCHAR(255) NULL'))
    if 'students' in table_columns and 'avatar' not in table_columns['students']:
        db.session.execute(text('ALTER TABLE students ADD COLUMN avatar VARCHAR(255) NULL'))
    account_tables = ['borrow_records', 'seat_reservations', 'book_favorites', 'book_reviews']
    for table in account_tables:
        if table in table_columns and 'teacher_id' not in table_columns[table]:
            db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN teacher_id INT NULL'))
    drift_columns = {
        'drift_books': ['provider_teacher_id', 'receiver_teacher_id'],
        'drift_requests': ['receiver_teacher_id'],
    }
    for table, columns in drift_columns.items():
        if table in table_columns:
            for column in columns:
                if column not in table_columns[table]:
                    db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} INT NULL'))
    db.session.commit()


def seed_default_publishers_and_teacher():
    default_publishers = ['人民邮电出版社', '机械工业出版社', '清华大学出版社', '电子工业出版社', '高等教育出版社', '人民文学出版社']
    for name in default_publishers:
        if not Publisher.query.filter_by(name=name).first():
            db.session.add(Publisher(name=name))

    if not Teacher.query.filter_by(job_no='T10001').first():
        teacher = Teacher(job_no='T10001', name='示例教师', department='图书馆')
        teacher.set_password('Teacher@123')
        db.session.add(teacher)
    db.session.commit()

if __name__ == '__main__':
    # 2. 借助应用上下文操作数据库
    with app.app_context():
        # 如果数据库中尚未建表，此命令会自动读取 app/models.py 并生成对应的表
        db.create_all()
        ensure_schema_compatibility()
        seed_default_publishers_and_teacher()
        print("数据库表结构已检查完毕 (如果不存在则已自动创建)。")
        
    # 3. 启动开发服务器
    # host='0.0.0.0' 允许局域网内的其他设备访问你的服务
    # debug=True 开启调试模式，代码修改后会自动重启服务器，并在网页上显示报错信息
    app.run(host='127.0.0.1', port=5000, debug=True)