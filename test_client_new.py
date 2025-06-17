import cv2                     # 导入OpenCV库，用于图像处理和显示
import numpy as np             # 导入NumPy库，用于处理数组数据
import requests                # 导入requests库，用于HTTP请求
from threading import Thread   # 导入Thread类，用于多线程
import time                    # 导入时间模块
import json                    # 导入JSON处理模块

class VideoStreamTester:
    def __init__(self, base_url):
        self.base_url = base_url                    # 保存基础URL
        self.video_url = f"{base_url}/video_feed"   # 视频流URL
        self.data_url = f"{base_url}/sensor_data"   # 传感器数据URL
        self.status_url = f"{base_url}/system_status" # 系统状态URL
        self.command_url = f"{base_url}/send_command" # 命令发送URL
        self.frame = None      # 当前帧，初始为None
        self.sensor_data = {}  # 传感器数据
        self.system_status = {} # 系统状态
        self.stopped = False   # 控制线程停止的标志

    def start(self):
        # 启动视频流线程
        Thread(target=self.update_video, args=()).start()
        # 启动数据获取线程
        Thread(target=self.update_data, args=()).start()
        return self                                 # 返回自身，方便链式调用

    def update_video(self):
        """更新视频流"""
        try:
            stream = requests.get(self.video_url, stream=True) # 以流模式请求视频流
            bytes_data = bytes()                         # 用于缓存接收到的字节数据

            for chunk in stream.iter_content(chunk_size=1024):  # 持续读取数据块
                if self.stopped:                        # 如果停止标志为True，则退出
                    return

                bytes_data += chunk                     # 累加接收到的数据
                a = bytes_data.find(b'\xff\xd8')        # 查找JPEG图片的起始标志
                b = bytes_data.find(b'\xff\xd9')        # 查找JPEG图片的结束标志

                if a != -1 and b != -1:                 # 如果找到了完整的JPEG图片
                    jpg = bytes_data[a:b+2]             # 截取完整的JPEG图片数据
                    bytes_data = bytes_data[b+2:]       # 剩余数据保留，等待下次处理
                    self.frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), 
                                            cv2.IMREAD_COLOR)  # 解码为OpenCV图像
        except Exception as e:
            print(f"视频流连接错误: {e}")

    def update_data(self):
        """定期获取传感器数据和系统状态"""
        while not self.stopped:
            try:
                # 获取传感器数据
                response = requests.get(self.data_url, timeout=1)
                if response.status_code == 200:
                    self.sensor_data = response.json()
                
                # 获取系统状态
                response = requests.get(self.status_url, timeout=1)
                if response.status_code == 200:
                    self.system_status = response.json()
                    
            except Exception as e:
                print(f"数据获取错误: {e}")
                
            time.sleep(0.1)  # 每100ms获取一次数据

    def send_command(self, action, params=None):
        """发送命令到服务器"""
        command = {'action': action, 'params': params or {}}
        try:
            response = requests.post(self.command_url, json=command, timeout=2)
            return response.json()
        except Exception as e:
            print(f"命令发送错误: {e}")
            return {'status': 'error', 'message': '发送失败'}

    def stop(self):
        self.stopped = True     # 设置停止标志，线程会自动退出

def test_with_data(stream):
    """测试视频流和数据传输"""
    prev_time = cv2.getTickCount()  # 获取初始时间戳
    
    while True:
        if stream.frame is not None:
            frame = stream.frame.copy()
            
            # 在视频上显示传感器数据
            if stream.sensor_data:
                data_text = f"Temp: {stream.sensor_data.get('temperature', 'N/A')}°C"
                cv2.putText(frame, data_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
                
                humidity_text = f"Humidity: {stream.sensor_data.get('humidity', 'N/A')}%"
                cv2.putText(frame, humidity_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
                
                frame_count = f"Frame: {stream.sensor_data.get('frame_count', 'N/A')}"
                cv2.putText(frame, frame_count, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
                
                motion_text = f"Motion: {stream.sensor_data.get('motion_detected', 'N/A')}"
                cv2.putText(frame, motion_text, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
            
            # 显示系统状态
            if stream.system_status:
                cpu_text = f"CPU: {stream.system_status.get('cpu_usage', 'N/A')}%"
                cv2.putText(frame, cpu_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (255, 0, 0), 2)
                
                memory_text = f"MEM: {stream.system_status.get('memory_usage', 'N/A')}%"
                cv2.putText(frame, memory_text, (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (255, 0, 0), 2)
                
                uptime = stream.system_status.get('uptime', 0)
                uptime_text = f"Uptime: {uptime}s"
                cv2.putText(frame, uptime_text, (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (255, 0, 0), 2)

            # 计算延迟
            curr_time = cv2.getTickCount()
            latency = (curr_time - prev_time) / cv2.getTickFrequency() * 1000
            latency_text = f"Latency: {latency:.2f}ms"
            cv2.putText(frame, latency_text, (10, 240), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 0, 255), 2)
            prev_time = curr_time
            
            cv2.imshow('HTTP Stream with Data', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):  # 按c发送命令
            result = stream.send_command('get_info')
            print(f"命令响应: {result}")
        elif key == ord('r'):  # 按r发送分辨率命令
            result = stream.send_command('set_camera_resolution', {'width': 1280, 'height': 720})
            print(f"分辨率设置响应: {result}")
        elif key == ord('s'):  # 按s显示所有数据
            print("=== 传感器数据 ===")
            print(json.dumps(stream.sensor_data, indent=2, ensure_ascii=False))
            print("=== 系统状态 ===")
            print(json.dumps(stream.system_status, indent=2, ensure_ascii=False))

def test_latency(stream):
    """原始延迟测试功能"""
    prev_time = cv2.getTickCount()  # 获取初始时间戳
    while True:
        if stream.frame is not None:    # 如果有新帧
            cv2.imshow('HTTP Stream Test', stream.frame)  # 显示当前帧

            curr_time = cv2.getTickCount()                # 获取当前时间戳
            latency = (curr_time - prev_time) / cv2.getTickFrequency() * 1000  # 计算延迟（毫秒）
            print(f"当前延迟: {latency:.2f}ms")            # 打印延迟
            prev_time = curr_time                         # 更新时间戳

        if cv2.waitKey(1) & 0xFF == ord('q'):             # 按下q键退出循环
            break

if __name__ == '__main__':
    base_url = "http://169.254.163.62:5000"  # 设置服务器基础URL

    print("正在连接视频流和数据服务...")         # 打印提示信息
    tester = VideoStreamTester(base_url).start()  # 创建并启动视频流测试器

    print("操作说明:")
    print("- 按 'q' 退出程序")
    print("- 按 'c' 发送测试命令")
    print("- 按 'r' 设置摄像头分辨率")
    print("- 按 's' 显示所有数据")

    try:
        test_with_data(tester)           # 开始带数据的测试
    finally:
        tester.stop()                  # 停止视频流线程
        cv2.destroyAllWindows()        # 关闭所有窗口
