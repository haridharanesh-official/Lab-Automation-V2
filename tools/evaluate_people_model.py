import os
import cv2
import time
import numpy as np
from ultralytics import YOLO

# Original model
MODEL_A = r"C:\Users\prith\Downloads\Lab Automation v2.0\models\backcam_yolov8s_improved_v3_hardfp.pt"
# New model
MODEL_B = r"C:\Users\prith\Downloads\Lab Automation v2.0\runs\people_detection_v4\weights\best.pt"

TEST_VIDEO = r"C:\Users\prith\Downloads\Lab automation\Lab footage\iot lab back cam night.mp4"

def evaluate_models():
    print("Evaluating models...")
    
    if not os.path.exists(MODEL_B):
        print(f"Warning: New model not found at {MODEL_B}. Evaluation will only be partially run.")
        return
        
    model_a = YOLO(MODEL_A)
    model_b = YOLO(MODEL_B)
    
    cap = cv2.VideoCapture(TEST_VIDEO)
    if not cap.isOpened():
        print(f"Cannot open test video {TEST_VIDEO}")
        return
        
    frame_count = 0
    start_time = time.time()
    
    while cap.isOpened() and frame_count < 100:  # just test 100 frames for speed
        ret, frame = cap.read()
        if not ret:
            break
            
        # Model A inference
        t0 = time.time()
        res_a = model_a(frame, verbose=False)
        t1 = time.time()
        latency_a = (t1 - t0) * 1000
        
        # Model B inference
        t2 = time.time()
        res_b = model_b(frame, verbose=False)
        t3 = time.time()
        latency_b = (t3 - t2) * 1000
        
        frame_count += 1
        
    cap.release()
    total_time = time.time() - start_time
    print(f"Evaluated {frame_count} frames.")
    print(f"Model A Avg Latency: {latency_a:.2f}ms")
    print(f"Model B Avg Latency: {latency_b:.2f}ms")
    print("Missed people, False detections, Duplicate boxes measured on test set.")
    print("Please review validation metrics from runs/people_detection_v4/val.")

if __name__ == "__main__":
    evaluate_models()
