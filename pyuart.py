import serial
def send_message_once(message='Hello, UART!'):
    """
    打开串口并发送一次信息的函数。

    参数:
    port -- 串口端口号（如 '/dev/ttyAMA0'）
    baudrate -- 波特率（如 115200）
    message -- 要发送的字符串信息
    """
    port='/dev/ttyAMA0'
    baudrate=115200
    try:
        # 打开串口
        ser = serial.Serial(port, baudrate)
        print("串口已打开：", ser.name)
        
        # 发送信息
        ser.write(message.encode('utf-8'))  # 将信息编码为 UTF-8 并发送
        print("发送信息：", message)
    except serial.SerialException as e:
        print("发送信息时发生错误：", e)
    finally:
        # 确保串口关闭
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

# 调用函数发送信息
#send_message_once('/dev/ttyAMA0', 115200, "Hello, UART!")

import serial

def receive_message(port='/dev/ttyAMA0', baudrate=115200, timeout=1):
    """
    打开串口并接收信息的函数。

    参数:
    port -- 串口端口号（如 '/dev/ttyAMA0'）
    baudrate -- 波特率（如 115200）
    timeout -- 超时时间（秒）

    返回:
    如果接收到 '1' 字符，返回 True；否则返回 False。
    """
    try:
        # 打开串口并设置超时时间
        ser = serial.Serial(port, baudrate, timeout=timeout)
        
        # 读取数据
        data = ser.readline()  # 读取一行数据
        cleaned_data = data.rstrip(b'\x00')  # 移除末尾的 \x00 字节
       # print("接收到的原始数据：", cleaned_data)
        
        # 解码为字符串
        decoded_data = cleaned_data.decode('ascii').strip()
        #print("解码后的数据：", decoded_data)
        
        # 判断是否接收到 '1'
        return decoded_data
    except serial.SerialException as e:
       # print("串口错误：", e)
        return False
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
'''
while True:
    if receive_message():
        print("接收到 'valid'，可以继续执行其他操作。")'''