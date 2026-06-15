import os
import cv2
from ultralytics import YOLO

MODEL_PATH = r"C:\Users\prith\Downloads\Lab Automation v2.0\models\backcam_yolov8s_improved_v3_hardfp.pt"
DATASET_TRAIN_DIR = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean\images\train"
DATASET_TRAIN_LBL = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean\labels\train"

VIDEOS = [
    r"C:\Users\prith\Downloads\Lab automation\Lab footage\iot lab back cam night.mp4"
]

def extract_hard_negatives(target_count=20):
    model = YOLO(MODEL_PATH)
    saved_count = 0
    
    os.makedirs(DATASET_TRAIN_DIR, exist_ok=True)
    os.makedirs(DATASET_TRAIN_LBL, exist_ok=True)
    
    for video_path in VIDEOS:
        if not os.path.exists(video_path):
            print(f"Video not found: {video_path}")
            continue
            
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0: fps = 30
        
        frame_idx = 0
        last_saved_frame = -9999
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Sample every second
            if frame_idx % fps == 0 and (frame_idx - last_saved_frame) > (fps * 5):
                results = model(frame, conf=0.25, verbose=False)
                
                # If no people detected (assuming empty lab)
                if len(results[0].boxes) == 0:
                    vid_name = os.path.splitext(os.path.basename(video_path))[0].replace(" ", "_")
                    img_name = f"hardneg_{vid_name}_f{frame_idx:06d}.jpg"
                    lbl_name = f"hardneg_{vid_name}_f{frame_idx:06d}.txt"
                    
                    img_path = os.path.join(DATASET_TRAIN_DIR, img_name)
                    lbl_path = os.path.join(DATASET_TRAIN_LBL, lbl_name)
                    
                    cv2.imwrite(img_path, frame)
                    with open(lbl_path, 'w') as f:
                        pass # Empty file
                        
                    saved_count += 1
                    last_saved_frame = frame_idx
                    print(f"Saved {img_name}")
                    
                    if saved_count >= target_count:
                        break
            
            frame_idx += 1
            
        cap.release()
        if saved_count >= target_count:
            break
            
    print(f"Total hard negatives saved: {saved_count}")

if __name__ == "__main__":
    extract_hard_negatives(20)
