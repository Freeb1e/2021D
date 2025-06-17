import cv2
import numpy as np
import requests
from threading import Thread, Lock
import time
import json
import uuid

class DualServerClient:
    def __init__(self, server1_url, server2_url):
        """
        双服务器运动检测客户端
        server1_url: 第一个服务器地址
        server2_url: 第二个服务器地址
        """
        self.server1_url = server1_url.rstrip('/')
        self.server2_url = server2_url.rstrip('/')
          # 为每个服务器创建独立的URL
        self.server1_video_url = f"{self.server1_url}/video_feed"
        self.server1_data_url = f"{self.server1_url}/motion_data"
        self.server1_ping_url = f"{self.server1_url}/ping"
        self.server1_control_url = f"{self.server1_url}/control"
        
        self.server2_video_url = f"{self.server2_url}/video_feed"
        self.server2_data_url = f"{self.server2_url}/motion_data"
        self.server2_ping_url = f"{self.server2_url}/ping"
        self.server2_control_url = f"{self.server2_url}/control"
        
        # 客户端标识
        self.client_id = str(uuid.uuid4())[:8]
        
        # 服务器1的数据
        self.server1_frame = None
        self.server1_motion_data = {'L': 0, 'T': 0, 'timestamp': 0}
        self.server1_connected = False
        
        # 服务器2的数据
        self.server2_frame = None
        self.server2_motion_data = {'L': 0, 'T': 0, 'timestamp': 0}
        self.server2_connected = False
          # 控制变量
        self.stopped = False
        self.data_lock = Lock()
        
        # 客户端控制状态
        self.valid_signal = False  # 当前发送给服务器的valid信号
        self.last_control_time = 0
        self.control_interval = 2.0  # 控制信号发送间隔（秒）
        
        # 统计信息
        self.server1_frame_count = 0
        self.server2_frame_count = 0
        self.last_stats_time = time.time()

    def start(self):
        """启动所有线程"""
        print(f"客户端ID: {self.client_id}")
        
        # 启动服务器1的线程
        Thread(target=self.update_server1_video, daemon=True).start()
        Thread(target=self.update_server1_data, daemon=True).start()
          # 启动服务器2的线程
        Thread(target=self.update_server2_video, daemon=True).start()
        Thread(target=self.update_server2_data, daemon=True).start()
        
        # 启动控制信号发送线程
        Thread(target=self.send_control_signals, daemon=True).start()
        
        return self

    def update_server1_video(self):
        """更新服务器1的视频流"""
        try:
            print(f"正在连接服务器1视频流: {self.server1_video_url}")
            stream = requests.get(self.server1_video_url, stream=True, timeout=10)
            self.server1_connected = True
            print("✓ 服务器1视频流连接成功")
            
            bytes_data = bytes()
            
            for chunk in stream.iter_content(chunk_size=1024):
                if self.stopped:
                    return
                    
                bytes_data += chunk
                
                # 查找JPEG边界
                start_pos = bytes_data.find(b'\xff\xd8')
                end_pos = bytes_data.find(b'\xff\xd9')
                
                if start_pos != -1 and end_pos != -1:
                    jpg_data = bytes_data[start_pos:end_pos+2]
                    bytes_data = bytes_data[end_pos+2:]
                    
                    # 解码图像
                    frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        with self.data_lock:
                            self.server1_frame = frame
                            self.server1_frame_count += 1
                    
        except Exception as e:
            print(f"✗ 服务器1视频流连接失败: {e}")
            self.server1_connected = False

    def update_server2_video(self):
        """更新服务器2的视频流"""
        try:
            print(f"正在连接服务器2视频流: {self.server2_video_url}")
            stream = requests.get(self.server2_video_url, stream=True, timeout=10)
            self.server2_connected = True
            print("✓ 服务器2视频流连接成功")
            
            bytes_data = bytes()
            
            for chunk in stream.iter_content(chunk_size=1024):
                if self.stopped:
                    return
                    
                bytes_data += chunk
                
                # 查找JPEG边界
                start_pos = bytes_data.find(b'\xff\xd8')
                end_pos = bytes_data.find(b'\xff\xd9')
                
                if start_pos != -1 and end_pos != -1:
                    jpg_data = bytes_data[start_pos:end_pos+2]
                    bytes_data = bytes_data[end_pos+2:]
                    
                    # 解码图像
                    frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        with self.data_lock:
                            self.server2_frame = frame
                            self.server2_frame_count += 1
                    
        except Exception as e:
            print(f"✗ 服务器2视频流连接失败: {e}")
            self.server2_connected = False

    def update_server1_data(self):
        """更新服务器1的运动检测数据"""
        while not self.stopped:
            try:
                response = requests.get(self.server1_data_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    with self.data_lock:
                        self.server1_motion_data = data
                        self.server1_motion_data['timestamp'] = time.time()
                        
            except Exception as e:
                print(f"服务器1数据获取失败: {e}")
            
            time.sleep(0.5)  # 每0.5秒获取一次数据

    def update_server2_data(self):
        """更新服务器2的运动检测数据"""
        while not self.stopped:
            try:
                response = requests.get(self.server2_data_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    with self.data_lock:
                        self.server2_motion_data = data
                        self.server2_motion_data['timestamp'] = time.time()
                        
            except Exception as e:
                print(f"服务器2数据获取失败: {e}")
            
            time.sleep(0.5)  # 每0.5秒获取一次数据

    def send_control_signals(self):
        """发送控制信号到两个服务器"""
        while not self.stopped:
            try:
                current_time = time.time()
                
                # 检查是否需要发送控制信号
                if current_time - self.last_control_time >= self.control_interval:
                    
                    # 准备发送的控制数据
                    control_data = {
                        'valid': self.valid_signal,
                        'client_id': self.client_id,
                        'timestamp': current_time
                    }
                    
                    # 发送到服务器1
                    self.send_control_to_server(self.server1_control_url, control_data, "服务器1")
                    
                    # 发送到服务器2
                    self.send_control_to_server(self.server2_control_url, control_data, "服务器2")
                    
                    self.last_control_time = current_time
                    
            except Exception as e:
                print(f"发送控制信号错误: {e}")
            
            time.sleep(0.5)  # 检查间隔

    def send_control_to_server(self, url, data, server_name):
        """向单个服务器发送控制信号"""
        try:
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=3
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    status_msg = "启动" if self.valid_signal else "停止"
                    print(f"✓ {server_name}摄像识别{status_msg}成功")
                else:
                    print(f"✗ {server_name}响应错误: {result.get('message', '未知错误')}")
            else:
                print(f"✗ {server_name}HTTP错误: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"✗ {server_name}控制信号发送超时")
        except requests.exceptions.ConnectionError:
            print(f"✗ {server_name}连接失败")
        except Exception as e:
            print(f"✗ {server_name}发送错误: {e}")

    def start_camera_detection(self):
        """启动摄像识别"""
        if not self.valid_signal:
            self.valid_signal = True
            self.last_control_time = 0  # 立即发送
            print("📹 启动两个服务器的摄像识别...")

    def stop_camera_detection(self):
        """停止摄像识别"""
        if self.valid_signal:
            self.valid_signal = False
            self.last_control_time = 0  # 立即发送
            print("⏹️ 停止两个服务器的摄像识别...")

    def toggle_camera_detection(self):
        """切换摄像识别状态"""
        if self.valid_signal:
            self.stop_camera_detection()
        else:
            self.start_camera_detection()

    def check_servers_status(self):
        status = {'server1': None, 'server2': None}
        
        try:
            response = requests.get(self.server1_ping_url, timeout=3)
            if response.status_code == 200:
                status['server1'] = response.json()
        except:
            pass
            
        try:
            response = requests.get(self.server2_ping_url, timeout=3)
            if response.status_code == 200:
                status['server2'] = response.json()
        except:
            pass
            
        return status

    def get_combined_display(self):
        """获取组合显示的图像"""
        with self.data_lock:
            frame1 = self.server1_frame.copy() if self.server1_frame is not None else None
            frame2 = self.server2_frame.copy() if self.server2_frame is not None else None
            data1 = self.server1_motion_data.copy()
            data2 = self.server2_motion_data.copy()
        
        # 创建占位图像
        placeholder = np.zeros((400, 400, 3), dtype=np.uint8)
        
        # 处理服务器1的帧
        if frame1 is not None:
            # 调整大小
            frame1 = cv2.resize(frame1, (400, 400))
            # 添加服务器1标识
            cv2.putText(frame1, "SERVER 1", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            # 添加连接状态
            status_color = (0, 255, 0) if self.server1_connected else (0, 0, 255)
            cv2.putText(frame1, f"连接: {'正常' if self.server1_connected else '断开'}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            # 添加L、T数据
            cv2.putText(frame1, f"L: {data1.get('L', 0):.1f}", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame1, f"T: {data1.get('T', 0):.2f}s", 
                       (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        else:
            frame1 = placeholder.copy()
            cv2.putText(frame1, "SERVER 1", (120, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame1, "无信号", (150, 220), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # 处理服务器2的帧
        if frame2 is not None:
            # 调整大小
            frame2 = cv2.resize(frame2, (400, 400))
            # 添加服务器2标识
            cv2.putText(frame2, "SERVER 2", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            # 添加连接状态
            status_color = (0, 255, 0) if self.server2_connected else (0, 0, 255)
            cv2.putText(frame2, f"连接: {'正常' if self.server2_connected else '断开'}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            # 添加L、T数据
            cv2.putText(frame2, f"L: {data2.get('L', 0):.1f}", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame2, f"T: {data2.get('T', 0):.2f}s", 
                       (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        else:
            frame2 = placeholder.copy()
            cv2.putText(frame2, "SERVER 2", (120, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame2, "无信号", (150, 220), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # 水平拼接两个视频流
        combined_frame = cv2.hconcat([frame1, frame2])
        
        # 添加整体信息
        cv2.putText(combined_frame, f"双服务器运动检测客户端 - ID: {self.client_id}",                   (10, combined_frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 添加控制状态
        control_text = f"摄像识别: {'运行中' if self.valid_signal else '已停止'}"
        control_color = (0, 255, 0) if self.valid_signal else (0, 0, 255)
        cv2.putText(combined_frame, control_text, 
                   (10, combined_frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, control_color, 2)
        
        return combined_frame, data1, data2

    def print_stats(self):
        """打印统计信息"""
        current_time = time.time()
        if current_time - self.last_stats_time >= 10:  # 每10秒打印一次
            print(f"\n=== 统计信息 ===")
            print(f"服务器1: 帧数={self.server1_frame_count}, 连接={'正常' if self.server1_connected else '断开'}")
            print(f"服务器2: 帧数={self.server2_frame_count}, 连接={'正常' if self.server2_connected else '断开'}")
            print(f"摄像识别: {'运行中' if self.valid_signal else '已停止'}")
            with self.data_lock:
                print(f"服务器1数据: L={self.server1_motion_data.get('L', 0):.1f}, T={self.server1_motion_data.get('T', 0):.2f}")
                print(f"服务器2数据: L={self.server2_motion_data.get('L', 0):.1f}, T={self.server2_motion_data.get('T', 0):.2f}")
            print("================\n")
            self.last_stats_time = current_time

    def stop(self):
        """停止客户端"""
        self.stopped = True

def main():
    """主函数"""
    print("=== 双服务器运动检测客户端 ===")
    
    # 获取服务器地址
    server1_ip = input("请输入服务器1的IP地址 (默认: 169.254.163.62): ").strip()
    if not server1_ip:
        server1_ip = "169.254.163.62"
    
    server1_port = input("请输入服务器1的端口 (默认: 5001): ").strip()
    if not server1_port:
        server1_port = "5001"
    
    server2_ip = input("请输入服务器2的IP地址 (默认: 169.254.163.62): ").strip()
    if not server2_ip:
        server2_ip = "169.254.163.62"
    
    server2_port = input("请输入服务器2的端口 (默认: 5002): ").strip()
    if not server2_port:
        server2_port = "5002"
    
    server1_url = f"http://{server1_ip}:{server1_port}"
    server2_url = f"http://{server2_ip}:{server2_port}"
    
    print(f"服务器1: {server1_url}")
    print(f"服务器2: {server2_url}")
    
    # 创建客户端
    client = DualServerClient(server1_url, server2_url)
    
    # 检查服务器状态
    print("检查服务器状态...")
    servers_status = client.check_servers_status()
    
    if servers_status['server1']:
        print(f"✓ 服务器1状态: {servers_status['server1'].get('message', '正常')}")
    else:
        print("✗ 服务器1无响应")
    
    if servers_status['server2']:
        print(f"✓ 服务器2状态: {servers_status['server2'].get('message', '正常')}")
    else:
        print("✗ 服务器2无响应")
    
    # 启动客户端
    client.start()
    
    # 等待连接建立
    print("等待连接建立...")
    time.sleep(3)
      # 控制说明
    print("\n=== 控制说明 ===")
    print("按 'q' 退出程序")
    print("按 's' 显示服务器状态")
    print("按 '1' 只显示服务器1")
    print("按 '2' 只显示服务器2")
    print("按 'b' 显示双屏模式")
    print("按 'i' 显示详细信息")
    print("按 'v' 切换摄像识别开关")
    print("按 'c' 启动摄像识别")
    print("按 'x' 停止摄像识别")
    print("================\n")
    
    # 显示模式：'dual'(双屏), 'server1'(仅服务器1), 'server2'(仅服务器2)
    display_mode = 'dual'
    show_info = True
    
    try:
        while True:
            if display_mode == 'dual':
                # 双屏显示模式
                combined_frame, data1, data2 = client.get_combined_display()
                cv2.imshow('双服务器运动检测客户端', combined_frame)
                
            elif display_mode == 'server1':
                # 仅显示服务器1
                with client.data_lock:
                    if client.server1_frame is not None:
                        frame = client.server1_frame.copy()
                        cv2.putText(frame, "仅服务器1模式", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow('双服务器运动检测客户端', frame)
                    
            elif display_mode == 'server2':
                # 仅显示服务器2
                with client.data_lock:
                    if client.server2_frame is not None:
                        frame = client.server2_frame.copy()
                        cv2.putText(frame, "仅服务器2模式", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        cv2.imshow('双服务器运动检测客户端', frame)
            
            # 打印统计信息
            if show_info:
                client.print_stats()
            
            # 按键处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):  # 显示服务器状态
                status = client.check_servers_status()
                print(f"\n服务器状态:")
                print(f"服务器1: {json.dumps(status['server1'], indent=2, ensure_ascii=False) if status['server1'] else '无响应'}")
                print(f"服务器2: {json.dumps(status['server2'], indent=2, ensure_ascii=False) if status['server2'] else '无响应'}")
            elif key == ord('1'):  # 切换到服务器1
                display_mode = 'server1'
                print("切换到服务器1显示模式")
            elif key == ord('2'):  # 切换到服务器2
                display_mode = 'server2'
                print("切换到服务器2显示模式")
            elif key == ord('b'):  # 切换到双屏模式
                display_mode = 'dual'
                print("切换到双屏显示模式")
            elif key == ord('i'):  # 切换信息显示
                show_info = not show_info
                print(f"详细信息显示: {'开启' if show_info else '关闭'}")
            elif key == ord('v'):  # 切换摄像识别
                client.toggle_camera_detection()
            elif key == ord('c'):  # 启动摄像识别
                client.start_camera_detection()
            elif key == ord('x'):  # 停止摄像识别
                client.stop_camera_detection()
                
    except KeyboardInterrupt:
        print("\n用户中断程序")
    finally:
        client.stop()
        cv2.destroyAllWindows()
        print("客户端已退出")

if __name__ == '__main__':
    main()