import cv2
import time
# # 初始化摄像头
cap = cv2.VideoCapture(0)
# 读取视频
#cap = cv2.VideoCapture('video.mp4')

# 读取第一帧
ret, frame1 = cap.read()
gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)

# 定义矩形结构元素
rectangle_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
count=0
count1=0
cxmax=0
cxmin=1000
start_time = time.perf_counter()
while True:
    # 读取下一帧
    ret, frame2 = cap.read()
    if not ret:
        break  # 如果视频结束，跳出循环

    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # 计算两帧的差异
    diff = cv2.absdiff(gray1, gray2)
    cv2.imshow('Frame Difference', diff)
    # 二值化以突出差异
    _, thresh = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)
    thresh = cv2.erode(thresh, rectangle_kernel, iterations=1)
    thresh = cv2.dilate(thresh, rectangle_kernel, iterations=2)  # 膨胀操作，使轮廓更清晰

    # 找出轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 识别面积最大的轮廓
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        cv2.rectangle(frame2, (x, y), (x + w, y + h), (0, 255, 0), 2)  # 用绿色矩形框出

        # 计算最大轮廓的中心坐标
        M = cv2.moments(largest_contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            # 在中心画一个红点
            cv2.circle(frame2, (cx, cy), 5, (0, 0, 255), -1)
            count+=1           
            if count1==0:
                print(count)
                if(count<50):
                    cxmax= cx if cx>cxmax else cxmax
                    cxmin= cx if cx<cxmin else cxmin
                else: 
                    end_time = time.perf_counter()
                    count=0
                    cxmid=(cxmax+cxmin)/2
                    print("cxmax=",cxmax,"cxmin",cxmin,"cxmid",cxmid)
                    cxmax=0
                    cxmin=1000
                    run_time = end_time - start_time
                    print("代码运行时间：", run_time, "秒")
                    start_time = time.perf_counter()
                    count1+=1
                    cxpast=cx
            else:               
                if((cxpast-cxmid)*(cx-cxmid)<0):
                    if count1==1:
                        start_time = time.perf_counter()
                    count1+=1
                    print("count1=", count1)
                    if count1==11:
                        count1=0
                        end_time = time.perf_counter()
                        run_time = end_time - start_time
                        print("五个周期所用时间：", run_time, "秒")
                    cxpast=cx
            # 可选：打印中心坐标
            #print(f"中心坐标: ({cx}, {cy})")

    # 显示结果
    thresh_img = cv2.merge([thresh, thresh, thresh])
    display_img = cv2.hconcat([frame2, thresh_img])
    # 压缩为原来的四分之一
    h, w = display_img.shape[:2]
    display_img_small = cv2.resize(display_img, (w // 2, h // 2))
    cv2.imshow('Difference', display_img_small)

    # 准备下一次迭代
    gray1 = gray2

    # 按'q'退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 释放资源
cap.release()
cv2.destroyAllWindows()