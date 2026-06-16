import cv2
import yaml
from ultralytics import YOLO

def main():
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    rtsp_url = config["camera"]["url"]
    model_path = config["model"]["path"]
    conf_thresh = config["model"]["confidence"]
    
    print(f"Loading model {model_path}...")
    model = YOLO(model_path)
    
    print(f"Connecting to RTSP stream: {rtsp_url}")
    # Using tcp transport for stability
    import os
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        print("Error: Could not open RTSP stream. Ensure the camera is online and the URL is correct.")
        return
        
    print("Stream connected. Press 'q' to quit, 't' to toggle bounding boxes.")
    
    show_boxes = True
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame. Reconnecting...")
            cap.release()
            import time
            time.sleep(2)
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            continue
            
        if show_boxes:
            results = model.track(frame, persist=True, classes=[0], conf=conf_thresh, verbose=False)
            display_frame = results[0].plot()
        else:
            display_frame = frame
            
        cv2.imshow("Live People Detection", display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('t'):
            show_boxes = not show_boxes
            print(f"Bounding boxes toggled: {'ON' if show_boxes else 'OFF'}")
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
