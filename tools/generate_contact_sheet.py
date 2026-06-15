import os
import glob
import cv2
import math
import numpy as np

REVIEW_DIR = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean\review\manual-label-review"
OUTPUT_PATH = r"C:\Users\prith\.gemini\antigravity\brain\093914c1-1584-43da-a868-4652cbd00049\contact_sheet.jpg"

def draw_boxes(img_path, lbl_path):
    img = cv2.imread(img_path)
    if img is None:
        return None
        
    h, w = img.shape[:2]
    
    with open(lbl_path, 'r') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) == 5:
            _, cx, cy, bw, bh = map(float, parts)
            x1 = int((cx - bw/2) * w)
            y1 = int((cy - bh/2) * h)
            x2 = int((cx + bw/2) * w)
            y2 = int((cy + bh/2) * h)
            
            # Use different colors to distinguish overlapping boxes
            color = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (0, 255, 255), (255, 0, 255), (255, 255, 0)][i % 6]
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, f"B{i}", (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
    # Add filename text
    filename = os.path.basename(img_path)
    cv2.putText(img, filename, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return img

def create_contact_sheet():
    img_files = glob.glob(os.path.join(REVIEW_DIR, '*.jpg'))
    if not img_files:
        print("No images found in review dir.")
        return
        
    images = []
    for img_path in img_files:
        lbl_path = os.path.splitext(img_path)[0] + '.txt'
        if os.path.exists(lbl_path):
            img_with_boxes = draw_boxes(img_path, lbl_path)
            if img_with_boxes is not None:
                images.append(img_with_boxes)
                
    if not images:
        print("Failed to process images.")
        return
        
    # Resize all to match the first image's aspect ratio/size for simplicity, or a fixed size
    target_w, target_h = 640, 360
    resized_images = [cv2.resize(img, (target_w, target_h)) for img in images]
    
    # Calculate grid size
    n = len(resized_images)
    cols = min(2, n)
    rows = math.ceil(n / cols)
    
    # Pad with blank images if necessary
    while len(resized_images) < rows * cols:
        resized_images.append(np.zeros((target_h, target_w, 3), dtype=np.uint8))
        
    # Stack images
    grid_rows = []
    for i in range(0, len(resized_images), cols):
        grid_rows.append(np.hstack(resized_images[i:i+cols]))
    contact_sheet = np.vstack(grid_rows)
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    cv2.imwrite(OUTPUT_PATH, contact_sheet)
    print(f"Contact sheet saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    create_contact_sheet()
