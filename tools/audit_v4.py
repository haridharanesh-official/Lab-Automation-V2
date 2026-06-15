import os
import glob
import yaml
import re

DATASET_PATH = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean"

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
    match = re.match(r"(.*)_f\d{6}", filename)
    if match: return match.group(1)
    return filename

def audit_v4():
    yaml_path = os.path.join(DATASET_PATH, 'data.yaml')
    with open(yaml_path, 'r') as f:
        data_config = yaml.safe_load(f)
        
    splits = ['train', 'val', 'test']
    
    stats = {
        'total_images': 0, 'missing_labels': 0, 'empty_labels': 0,
        'invalid_boxes': 0, 'exact_duplicates': 0, 'high_iou_duplicates': 0,
        'sequence_leakage': 0
    }
    
    seq_to_split = {}
    
    for split in splits:
        split_img_dir = os.path.join(DATASET_PATH, f'images/{split}')
        split_lbl_dir = os.path.join(DATASET_PATH, f'labels/{split}')
        
        if not os.path.exists(split_img_dir): continue
        
        for img_path in glob.glob(os.path.join(split_img_dir, '*.jpg')):
            stats['total_images'] += 1
            img_name = os.path.basename(img_path)
            lbl_name = os.path.splitext(img_name)[0] + '.txt'
            lbl_path = os.path.join(split_lbl_dir, lbl_name)
            
            seq_name = get_sequence_name(img_name)
            if seq_name not in seq_to_split:
                seq_to_split[seq_name] = split
            elif seq_to_split[seq_name] != split:
                stats['sequence_leakage'] += 1
                
            if not os.path.exists(lbl_path):
                stats['missing_labels'] += 1
                continue
                
            with open(lbl_path, 'r') as f:
                lines = f.readlines()
                
            if not lines:
                stats['empty_labels'] += 1
                continue
                
            boxes = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) == 5:
                    boxes.append(tuple(map(float, parts[1:])))
                else:
                    stats['invalid_boxes'] += 1
                    
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    iou = calculate_iou(boxes[i], boxes[j])
                    if iou == 1.0:
                        stats['exact_duplicates'] += 1
                    elif iou > 0.5:
                        stats['high_iou_duplicates'] += 1

    report_path = r"C:\Users\prith\Downloads\Lab Automation v2.0\docs\dataset-audit-report.md"
    with open(report_path, 'w') as f:
        f.write("# Dataset Audit Report (v4_clean)\n\n")
        f.write("## Overview\n")
        f.write(f"- Dataset: `{DATASET_PATH}`\n")
        f.write(f"- Total Images: {stats['total_images']}\n")
        f.write(f"- Empty Labels (Hard Negatives): {stats['empty_labels']}\n")
        f.write(f"- Missing Labels: {stats['missing_labels']}\n")
        f.write("\n## Issues Found\n")
        f.write(f"- Sequence Leakage: {stats['sequence_leakage']} frames\n")
        f.write(f"- Exact Duplicates: {stats['exact_duplicates']}\n")
        f.write(f"- Invalid Boxes: {stats['invalid_boxes']}\n")
        f.write(f"- High IoU Duplicate Boxes (Unresolved): {stats['high_iou_duplicates']}\n")
        
    print(f"Audit complete. Total Hard Negatives: {stats['empty_labels']}. Unresolved High IoU: {stats['high_iou_duplicates']}")

if __name__ == "__main__":
    audit_v4()
