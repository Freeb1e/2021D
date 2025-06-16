from flask import Flask, Response
import cv2
import threading

app = Flask(__name__)

# 全局变量存储摄像头帧
frame = None
lock = threading.Lock()

def generate_frames():
    """生成摄像头帧的线程函数"""
    global frame
    camera = cv2.VideoCapture(1)  # 使用第二个摄像头，如果没有则改为0
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # 设置帧宽度
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # 设置帧高度
    
    # 如果第二个摄像头不可用，则使用第一个摄像头
    if not camera.isOpened():
        camera = cv2.VideoCapture(0)
    
    while True:
        success, img = camera.read()  # 读取摄像头帧
        if not success:               # 如果读取失败则退出
            break
        
        # 在图像上添加服务器标识
        cv2.putText(img, 'Server 2', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # 线程安全地更新全局帧数据
        with lock:
            _, buffer = cv2.imencode('.jpg', img)  # 将图像编码为JPEG格式
            frame = buffer.tobytes()               # 转换为字节数据
        
        # 控制帧率约30fps
        threading.Event().wait(0.03)

@app.route('/')
def index():
    """主页路由，显示网页界面"""
    return """
    <h1>Flask视频流测试 - 服务器2</h1>
    <img src="/video_feed" width="640">
    <p>访问 /video_feed 获取原始视频流</p>
    <p>服务器端口: 5002</p>
    """

@app.route('/video_feed')
def video_feed():
    """视频流路由，返回MJPEG流"""
    def generate():
        global frame
        while True:
            with lock:  # 线程安全地访问帧数据
                if frame is not None:
                    # 生成MJPEG流格式的响应
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           frame + b'\r\n')
            
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # 启动摄像头线程（守护线程，主程序退出时自动结束）
    threading.Thread(target=generate_frames, daemon=True).start()
    
    # 启动Flask服务器，监听5002端口
    print("服务器2启动在端口5002...")
    app.run(host='0.0.0.0', port=5002, threaded=True)
