import os
import glob
import shutil

DATASET_PATH = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean"
REVIEW_DIR = os.path.join(DATASET_PATH, "review", "manual-label-review")

def calculate_iou(box1, box2):
    x1_min, y1_min = box1[0] - box1[2]/2, box1[1] - box1[3]/2
    x1_max, y1_max = box1[0] + box1[2]/2, box1[1] + box1[3]/2
    x2_min, y2_min = box2[0] - box2[2]/2, box2[1] - box2[3]/2
    x2_max, y2_max = box2[0] + box2[2]/2, box2[1] + box2[3]/2

    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)

    if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
        return 0.0

    inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = box1_area + box2_area - inter_area

    if union_area == 0:
        return 0.0
    return inter_area / union_area

def fix_dataset():
    print("Fixing flagged issues...")
    lbl_files = glob.glob(os.path.join(REVIEW_DIR, '*.txt'))
    
    for review_lbl in lbl_files:
        lbl_name = os.path.basename(review_lbl)
        
        # Find it in main dataset
        train_lbl = os.path.join(DATASET_PATH, 'labels', 'train', lbl_name)
        val_lbl = os.path.join(DATASET_PATH, 'labels', 'val', lbl_name)
        test_lbl = os.path.join(DATASET_PATH, 'labels', 'test', lbl_name)
        
        target_path = None
        if os.path.exists(train_lbl): target_path = train_lbl
        elif os.path.exists(val_lbl): target_path = val_lbl
        elif os.path.exists(test_lbl): target_path = test_lbl
        
        if not target_path:
            continue
            
        with open(target_path, 'r') as f:
            lines = f.readlines()
            
        boxes = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) == 5:
                class_id = int(parts[0])
                x, y, w, h = map(float, parts[1:])
                # filter out very small boxes
                if w * h >= 0.001:
                    boxes.append((class_id, x, y, w, h, line))
                    
        # Apply NMS (IoU threshold 0.7)
        boxes_to_keep = []
        # Sort boxes by area descending to keep the larger box when merging duplicates
        boxes.sort(key=lambda b: b[3]*b[4], reverse=True)
        
        for i in range(len(boxes)):
            keep = True
            for j in range(len(boxes_to_keep)):
                if calculate_iou(boxes[i][1:5], boxes_to_keep[j][1:5]) > 0.7:
                    keep = False
                    break
            if keep:
                boxes_to_keep.append(boxes[i])
                
        with open(target_path, 'w') as f:
            for b in boxes_to_keep:
                f.write(b[5])
                
    print("Flagged issues fixed in main dataset.")

if __name__ == "__main__":
    fix_dataset()
