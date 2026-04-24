from app import create_app, db

# 1. 调用工厂函数，创建 Flask 应用实例
app = create_app()

if __name__ == '__main__':
    # 2. 借助应用上下文操作数据库
    with app.app_context():
        # 如果数据库中尚未建表，此命令会自动读取 app/models.py 并生成对应的表
        db.create_all()
        print("数据库表结构已检查完毕 (如果不存在则已自动创建)。")
        
    # 3. 启动开发服务器
    # host='0.0.0.0' 允许局域网内的其他设备访问你的服务
    # debug=True 开启调试模式，代码修改后会自动重启服务器，并在网页上显示报错信息
    app.run(host='127.0.0.1', port=5000, debug=True)