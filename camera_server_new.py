from flask import Flask, Response, jsonify, request
import cv2
import threading
import time
import json
import random

app = Flask(__name__)

# 记录服务器启动时间
start_time = time.time()

# 全局变量存储摄像头帧和其他数据
frame = None
sensor_data = {}
system_status = {}
lock = threading.Lock()
frame_count = 0

def generate_frames():
    global frame, sensor_data, system_status, frame_count
    camera = cv2.VideoCapture(0)  # 使用默认摄像头
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    while True:
        success, img = camera.read()
        if not success:
            break
        
        frame_count += 1
        
        # 生成模拟传感器数据
        with lock:
            _, buffer = cv2.imencode('.jpg', img)
            frame = buffer.tobytes()
            
            # 更新传感器数据 (模拟真实传感器)
            sensor_data = {
                'timestamp': time.time(),
                'temperature': round(20 + random.uniform(-5, 15), 1),  # 15-35°C
                'humidity': round(40 + random.uniform(-10, 30), 1),    # 30-70%
                'pressure': round(1013 + random.uniform(-50, 50), 1),  # 气压
                'light_level': random.randint(0, 1023),                # 光照传感器
                'motion_detected': random.choice([True, False]),       # 运动检测
                'frame_count': frame_count
            }
            
            # 更新系统状态
            system_status = {
                'cpu_usage': round(random.uniform(10, 80), 1),         # CPU使用率
                'memory_usage': round(random.uniform(30, 90), 1),      # 内存使用率
                'disk_usage': round(random.uniform(20, 95), 1),        # 磁盘使用率
                'network_speed': round(random.uniform(1, 100), 2),     # 网络速度 Mbps
                'uptime': int(time.time() - start_time),               # 运行时间(秒)
                'camera_status': 'online',
                'last_update': time.time()
            }
        
        # 控制帧率
        threading.Event().wait(0.03)  # ~30fps

@app.route('/')
def index():
    return """
    <h1>Flask视频流测试服务器</h1>
    <img src="/video_feed" width="640" height="480">
    <h2>API端点说明:</h2>
    <ul>
        <li><a href="/video_feed">/video_feed</a> - 获取视频流</li>
        <li><a href="/sensor_data">/sensor_data</a> - 获取传感器数据</li>
        <li><a href="/system_status">/system_status</a> - 获取系统状态</li>
        <li><a href="/all_data">/all_data</a> - 获取所有数据</li>
        <li>/send_command (POST) - 发送控制命令</li>
    </ul>
    <h2>传感器数据实时预览:</h2>
    <div id="sensor-data">加载中...</div>
    <h2>系统状态实时预览:</h2>
    <div id="system-status">加载中...</div>
    
    <script>
        function updateData() {
            fetch('/sensor_data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('sensor-data').innerHTML = 
                        '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                });
                
            fetch('/system_status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('system-status').innerHTML = 
                        '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                });
        }
        
        // 每秒更新一次数据
        setInterval(updateData, 1000);
        updateData(); // 立即执行一次
    </script>
    """

@app.route('/video_feed')
def video_feed():
    def generate():
        global frame
        while True:
            with lock:
                if frame is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           frame + b'\r\n')
            
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/sensor_data')
def get_sensor_data():
    """获取实时传感器数据"""
    with lock:
        return jsonify(sensor_data)

@app.route('/system_status')
def get_system_status():
    """获取系统状态信息"""
    with lock:
        return jsonify(system_status)

@app.route('/send_command', methods=['POST'])
def send_command():
    """接收来自客户端的命令"""
    try:
        command = request.get_json()
        print(f"收到命令: {command}")
        
        # 这里可以处理各种命令
        action = command.get('action', 'unknown')
        params = command.get('params', {})
        
        # 模拟命令处理
        response = {
            'status': 'success',
            'message': f"命令 '{action}' 已执行",
            'timestamp': time.time(),
            'result': process_command(action, params)
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'命令处理失败: {str(e)}',
            'timestamp': time.time()
        }), 400

def process_command(action, params):
    """处理具体命令"""
    if action == 'set_camera_resolution':
        width = params.get('width', 640)
        height = params.get('height', 480)
        return f"摄像头分辨率设置为 {width}x{height}"
    elif action == 'get_info':
        return "服务器运行正常"
    elif action == 'reboot':
        return "重启命令已接收（模拟）"
    elif action == 'set_threshold':
        threshold = params.get('threshold', 30)
        return f"检测阈值设置为 {threshold}"
    elif action == 'toggle_motion_detection':
        enabled = params.get('enabled', True)
        return f"运动检测{'开启' if enabled else '关闭'}"
    else:
        return f"未知命令: {action}"

@app.route('/all_data')
def get_all_data():
    """一次性获取所有数据"""
    with lock:
        return jsonify({
            'sensor_data': sensor_data,
            'system_status': system_status,
            'timestamp': time.time()
        })

@app.route('/ping')
def ping():
    """健康检查端点"""
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'uptime': int(time.time() - start_time)
    })

if __name__ == '__main__':
    print("正在启动Flask服务器...")
    print("摄像头初始化中...")
    
    # 启动摄像头线程
    camera_thread = threading.Thread(target=generate_frames, daemon=True)
    camera_thread.start()
    
    print("服务器启动完成！")
    print("访问 http://localhost:5000 查看web界面")
    print("访问 http://localhost:5000/video_feed 查看视频流")
    print("按 Ctrl+C 停止服务器")
    
    # 启动Flask服务器
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n服务器已停止")
