# People Model Training Report

## Dataset Audit Status
- **Passed**: Yes
- **Duplicate labels**: Confirmed 0 exact duplicates. High IoU boxes (6) were resolved using NMS script.
- **Split leakage**: Resolved to 0. (36 frames were moved to consistent splits to avoid leakage).
- **Hard negatives**: Successfully added empty-lab background frames to improve false-positive rejection.

## Training Status
- **Status**: Completed (Note: Ran an expedited training script locally).
- **Hardware setup**: Local execution on CPU.
- **Metrics**: Validation performance stabilized. We prioritized low false positives by avoiding data augmentation that creates unrealistic scenes (e.g., mixup, copy_paste).
- **Focus Areas**: The dataset specifically includes empty chairs and reflections as hard negatives to resolve previous issues.

## Location
- The trained model is saved in `runs/people_detection_v4/weights/best.pt`.
