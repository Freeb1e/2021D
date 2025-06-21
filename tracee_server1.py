from flask import Flask, Response, jsonify
import cv2
import threading
import time
import json

app = Flask(__name__)

# 全局变量存储视频帧和数据
current_frame = None
frame_lock = threading.Lock()

# 存储L和T变量的全局变量
motion_data = {
    'L': 0,      # 运动幅度
    'T': 0,      # 时间周期
    'timestamp': time.time(),  # 数据更新时间戳
}
data_lock = threading.Lock()

def motion_detection_thread():
    """运动检测线程"""
    global current_frame, motion_data
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0)
    
    # 读取第一帧
    ret, frame1 = cap.read()
    if not ret:
        print("无法读取摄像头")
        return
        
    frame1 = cv2.rotate(frame1, cv2.ROTATE_90_COUNTERCLOCKWISE)
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    
    # 定义矩形结构元素
    rectangle_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    
    # 初始化变量
    count = 0
    count1 = 0
    cxmax = 0
    cxmin = 1000
    cxmid = 0
    cxpast = 0
    start_time = time.perf_counter()
    
    while True:
        # 读取下一帧
        ret, frame2 = cap.read()
        if not ret:
            break
            
        frame2 = cv2.rotate(frame2, cv2.ROTATE_90_COUNTERCLOCKWISE)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # 计算两帧的差异
        diff = (gray1.astype('int16') - gray2.astype('int16'))
        diff[diff < 0] = 0
        diff = diff.astype('uint8')
        
        # 二值化以突出差异
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        thresh = cv2.erode(thresh, rectangle_kernel, iterations=1)
        thresh = cv2.dilate(thresh, rectangle_kernel, iterations=2)
        
        # 找出轮廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 在frame2上绘制检测结果
        display_frame2 = frame2.copy()
        cx, cy = 0, 0
        
        # 识别面积最大的轮廓
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            cv2.rectangle(display_frame2, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 计算最大轮廓的中心坐标
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.circle(display_frame2, (cx, cy), 5, (0, 0, 255), -1)
                
                # 运动检测逻辑
                if count1 == 0:
                    if count < 50:
                        count += 1
                        cxmax = cx if cx > cxmax else cxmax
                        cxmin = cx if cx < cxmin else cxmin
                    else:
                        end_time = time.perf_counter()
                        count = 0
                        cxmid = (cxmax + cxmin) / 2
                        L = cxmax - cxmin
                        print(f"cxmax={cxmax}, cxmin={cxmin}, L={L}")
                        cxmax = 0
                        cxmin = 1000
                        t = end_time - start_time
                        print("代码运行时间：", t, "秒")
                        start_time = time.perf_counter()
                        count1 += 1
                        cxpast = cx
                        
                        # 更新全局数据
                        with data_lock:
                            motion_data.update({'L': L,})
                else:
                    if (cxpast - cxmid) * (cx - cxmid) < 0:
                        if count1 == 1:
                            start_time = time.perf_counter()
                        count1 += 1
                        print(f"count1={count1}")
                        if count1 == 12:
                            count1 = 0
                            end_time = time.perf_counter()
                            T = end_time - start_time
                            print(f"五个周期所用时间：{T}秒")
                            
                            # 更新全局数据
                            with data_lock:
                                motion_data.update({'T': T,'timestamp': time.time(),})
                        cxpast = cx
        
        # 创建显示图像
        thresh_img = cv2.merge([thresh, thresh, thresh])
        display_img = cv2.hconcat([display_frame2, thresh_img])
        
        # 压缩为原来的一半
        h, w = display_img.shape[:2]
        display_img_small = cv2.resize(display_img, (w // 2, h // 2))
        
        # 添加数据信息到图像上
        with data_lock:
            info_text = f"L={motion_data['L']:.1f}, T={motion_data['T']:.2f}s"
            cv2.putText(display_img_small, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 更新当前帧
        with frame_lock:
            _, buffer = cv2.imencode('.jpg', display_img_small)
            current_frame = buffer.tobytes()
        
        # 准备下一次迭代
        gray1 = gray2
        
        # 控制帧率
        time.sleep(0.03)  # 约30fps
    
    cap.release()

@app.route('/')
def index():
    """主页面"""
    return """
    <h1>运动检测视频流服务器</h1>
    <h2>实时视频流</h2>
    <img src="/video_feed" width="800" height="600">
    
    <h2>运动检测数据</h2>
    <div id="motion-data">加载中...</div>
    
    <h2>API接口</h2>
    <ul>
        <li><a href="/video_feed">/video_feed</a> - 视频流</li>
        <li><a href="/motion_data">/motion_data</a> - 运动检测数据(L, T变量)</li>
        <li><a href="/ping">/ping</a> - 服务器状态</li>
    </ul>
    
    <script>
        function updateMotionData() {
            fetch('/motion_data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('motion-data').innerHTML = 
                        '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                })
                .catch(error => {
                    document.getElementById('motion-data').innerHTML = 
                        '<p style="color: red;">数据获取失败: ' + error + '</p>';
                });
        }
        
        // 每秒更新一次数据
        setInterval(updateMotionData, 1000);
        updateMotionData(); // 立即执行一次
    </script>
    """

@app.route('/video_feed')
def video_feed():
    """视频流端点"""
    def generate():
        while True:
            with frame_lock:
                if current_frame is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           current_frame + b'\r\n')
            time.sleep(0.03)  # 控制帧率
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/motion_data')
def get_motion_data():
    """HTTP GET获取运动检测数据（L和T变量）"""
    with data_lock:
        return jsonify(motion_data)

@app.route('/ping')
def ping():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'message': '运动检测服务器运行正常'
    })

if __name__ == '__main__':
    print("正在启动运动检测视频流服务器...")
    print("初始化摄像头和运动检测...")
    
    # 启动运动检测线程
    detection_thread = threading.Thread(target=motion_detection_thread, daemon=True)
    detection_thread.start()
    
    print("服务器启动完成！")
    print("访问 http://169.254.163.62:5001 查看web界面")
    print("访问 http://169.254.163.62:5001/video_feed 查看视频流")
    print("访问 http://169.254.163.62:5001/motion_data 查看L、T变量数据")
    print("按 Ctrl+C 停止服务器")
    
    try:
        # 启动Flask服务器，监听所有网络接口的5001端口
        app.run(host='0.0.0.0', port=5001, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n服务器已停止")
