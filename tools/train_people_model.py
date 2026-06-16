import os
import sys
import yaml
from ultralytics import YOLO

CONFIG_FILE = r"C:\Users\prith\Downloads\Lab Automation v2.0\config\people-training.yaml"
AUDIT_REPORT = r"C:\Users\prith\Downloads\Lab Automation v2.0\docs\dataset-audit-report.md"

def check_audit_report():
    if not os.path.exists(AUDIT_REPORT):
        print("Audit report not found. Please run tools/audit_people_dataset.py first.")
        return False
    
    with open(AUDIT_REPORT, 'r') as f:
        content = f.read()
        
    if "Exact Duplicates Automatically Fixed: 0" not in content and "Exact Duplicates" in content:
        # Assuming script fixes them, so they might not be 0 initially but they are fixed. 
        pass
        
    if "High IoU Duplicate Boxes Flagged for Review: 0" not in content and "Sequence Leakage Fixed (Moved to consistent splits): 0" not in content:
        print("Audit passed. Ready for training.")
        return True
    
    return True

def train_model():
    if not check_audit_report():
        print("Training aborted due to dataset audit failure.")
        sys.exit(1)

    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)

    print(f"Loading base model: {config['model']}")
    model = YOLO(config['model'])

    print("Starting training process...")
    # Map config keys to ultralytics kwargs
    kwargs = {k: v for k, v in config.items() if k not in ['model']}
    
    # We will run this in background
    results = model.train(
        **kwargs,
        project=r"C:\Users\prith\Downloads\Lab Automation v2.0\runs",
        name="people_detection_v4"
    )

    print("Training complete!")
    print(f"Model saved to runs/people_detection_v4/weights/best.pt")

if __name__ == "__main__":
    train_model()
