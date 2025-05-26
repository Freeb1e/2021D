import cv2

# # 初始化摄像头
cap = cv2.VideoCapture(0)
# 读取视频
#cap = cv2.VideoCapture('video.mp4')

# 读取第一帧
ret, frame1 = cap.read()
gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)

# 定义矩形结构元素
rectangle_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

while True:
    # 读取下一帧
    ret, frame2 = cap.read()
    if not ret:
        break  # 如果视频结束，跳出循环

    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # 计算两帧的差异
    diff = cv2.absdiff(gray1, gray2)

    # 二值化以突出差异
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    thresh = cv2.dilate(thresh, rectangle_kernel, iterations=2)  # 膨胀操作，使轮廓更清晰

    # 找出轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 识别面积最大的轮廓
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        cv2.rectangle(frame2, (x, y), (x + w, y + h), (0, 255, 0), 2)  # 用绿色矩形框出

    # 显示结果
    thresh_img = cv2.merge([thresh, thresh, thresh])
    cv2.imshow('Difference', cv2.hconcat([frame2, thresh_img]))
    # 准备下一次迭代
    gray1 = gray2

    # 按'q'退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 释放资源
cap.release()
cv2.destroyAllWindows()
