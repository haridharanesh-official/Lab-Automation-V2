import os
import glob
import shutil
import yaml
import re

ORIGINAL_DATASET_PATH = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_improved_v3_hardfp"
NEW_DATASET_PATH = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean"
REVIEW_DIR = os.path.join(NEW_DATASET_PATH, "review", "manual-label-review")

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

    if union_area == 0: return 0.0
    return inter_area / union_area

def get_sequence_name(filename):
    # Extracts the sequence name, assuming format prefix_f000000_suffix
    match = re.match(r"(.*)_f\d{6}", filename)
    if match:
        return match.group(1)
    return "unknown"

def audit_and_clean_dataset():
    print(f"Starting dataset audit. Clean dataset will be at: {NEW_DATASET_PATH}")
    if os.path.exists(NEW_DATASET_PATH):
        shutil.rmtree(NEW_DATASET_PATH)
    
    os.makedirs(REVIEW_DIR, exist_ok=True)
    
    yaml_path = os.path.join(ORIGINAL_DATASET_PATH, 'data.yaml')
    with open(yaml_path, 'r') as f:
        data_config = yaml.safe_load(f)
        
    splits = ['train', 'val', 'test']
    
    # We will build a list of all images, identify sequences, and enforce split separation.
    all_images = []
    
    for split in splits:
        split_img_dir = os.path.join(ORIGINAL_DATASET_PATH, data_config.get(split, f'images/{split}'))
        split_lbl_dir = split_img_dir.replace('images', 'labels')
        
        if not os.path.exists(split_img_dir):
            continue
            
        for img_path in glob.glob(os.path.join(split_img_dir, '*.jpg')):
            img_name = os.path.basename(img_path)
            lbl_name = os.path.splitext(img_name)[0] + '.txt'
            lbl_path = os.path.join(split_lbl_dir, lbl_name)
            
            seq_name = get_sequence_name(img_name)
            all_images.append({
                'img_path': img_path,
                'lbl_path': lbl_path,
                'img_name': img_name,
                'lbl_name': lbl_name,
                'original_split': split,
                'seq_name': seq_name
            })
            
    # Resolve sequence leakage. Assign each sequence to the first split it appeared in.
    seq_to_split = {}
    leakage_resolved = 0
    
    # Process images and copy to new location
    stats = {
        'total_images': 0, 'missing_labels': 0, 'empty_labels': 0,
        'invalid_boxes': 0, 'exact_duplicates_fixed': 0, 'high_iou_duplicates': 0,
        'sequence_leakage_resolved': 0, 'suspicious_small_boxes': 0
    }
    
    for split in splits:
        os.makedirs(os.path.join(NEW_DATASET_PATH, f'images/{split}'), exist_ok=True)
        os.makedirs(os.path.join(NEW_DATASET_PATH, f'labels/{split}'), exist_ok=True)

    for item in all_images:
        seq_name = item['seq_name']
        original_split = item['original_split']
        
        if seq_name not in seq_to_split:
            seq_to_split[seq_name] = original_split
            target_split = original_split
        else:
            target_split = seq_to_split[seq_name]
            if target_split != original_split:
                stats['sequence_leakage_resolved'] += 1
                
        # Now process the label and image
        img_path = item['img_path']
        lbl_path = item['lbl_path']
        img_name = item['img_name']
        lbl_name = item['lbl_name']
        
        new_img_dir = os.path.join(NEW_DATASET_PATH, f'images/{target_split}')
        new_lbl_dir = os.path.join(NEW_DATASET_PATH, f'labels/{target_split}')
        
        new_img_path = os.path.join(new_img_dir, img_name)
        new_lbl_path = os.path.join(new_lbl_dir, lbl_name)
        
        stats['total_images'] += 1
        
        # Copy image
        shutil.copy(img_path, new_img_path)
        
        if not os.path.exists(lbl_path):
            stats['missing_labels'] += 1
            continue
            
        with open(lbl_path, 'r') as f:
            lines = f.readlines()
            
        if not lines:
            stats['empty_labels'] += 1
            # Write empty file
            open(new_lbl_path, 'w').close()
            continue
            
        boxes = []
        has_review_issue = False
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                stats['invalid_boxes'] += 1
                has_review_issue = True
                continue
                
            class_id = int(parts[0])
            x, y, w, h = map(float, parts[1:])
            
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
                stats['invalid_boxes'] += 1
                has_review_issue = True
                continue
                
            if w * h < 0.001:
                stats['suspicious_small_boxes'] += 1
                has_review_issue = True
                
            boxes.append((class_id, x, y, w, h, line))
            
        boxes_to_keep = []
        for i in range(len(boxes)):
            is_duplicate = False
            for j in range(i + 1, len(boxes)):
                iou = calculate_iou(boxes[i][1:5], boxes[j][1:5])
                if iou == 1.0: # Exact duplicate
                    is_duplicate = True
                    stats['exact_duplicates_fixed'] += 1
                    break
                elif iou > 0.5: # Ambiguous overlapping duplicate
                    has_review_issue = True
                    stats['high_iou_duplicates'] += 1
                    
            if not is_duplicate:
                boxes_to_keep.append(boxes[i])
                
        with open(new_lbl_path, 'w') as f:
            for b in boxes_to_keep:
                f.write(b[5])
                
        if has_review_issue:
            # Copy original to review folder
            shutil.copy(img_path, os.path.join(REVIEW_DIR, img_name))
            shutil.copy(lbl_path, os.path.join(REVIEW_DIR, lbl_name))
            
    # Write new data.yaml
    with open(os.path.join(NEW_DATASET_PATH, 'data.yaml'), 'w') as f:
        f.write("path: " + NEW_DATASET_PATH.replace("\\", "/") + "\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("test: images/test\n")
        f.write("names:\n  0: person\n")

    # Write report
    report_path = r"C:\Users\prith\Downloads\Lab Automation v2.0\docs\dataset-audit-report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        f.write("# Dataset Audit Report\n\n")
        f.write("## Overview\n")
        f.write(f"- Original Dataset: `{ORIGINAL_DATASET_PATH}`\n")
        f.write(f"- Cleaned Dataset: `{NEW_DATASET_PATH}`\n")
        f.write(f"- Total Images: {stats['total_images']}\n")
        f.write(f"- Empty Labels (Hard Negatives): {stats['empty_labels']}\n")
        f.write(f"- Missing Labels: {stats['missing_labels']}\n")
        f.write("\n## Issues Found & Action Taken\n")
        f.write(f"- Sequence Leakage Fixed (Moved to consistent splits): {stats['sequence_leakage_resolved']} frames\n")
        f.write(f"- Exact Duplicates Automatically Fixed: {stats['exact_duplicates_fixed']}\n")
        f.write(f"- Invalid Boxes Removed/Flagged: {stats['invalid_boxes']}\n")
        f.write(f"- Suspicious Small Boxes Flagged for Review: {stats['suspicious_small_boxes']}\n")
        f.write(f"- High IoU Duplicate Boxes Flagged for Review: {stats['high_iou_duplicates']}\n")
        f.write("\n## Next Steps\n")
        f.write("- Review images and labels in the `review/manual-label-review/` directory inside the new dataset folder.\n")
        
    print(f"Audit complete. Report generated at {report_path}.")

if __name__ == "__main__":
    audit_and_clean_dataset()
