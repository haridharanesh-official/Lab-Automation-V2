# Dataset Audit Report

## Overview
- Original Dataset: `C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_improved_v3_hardfp`
- Cleaned Dataset: `C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean`
- Total Images: 123
- Empty Labels (Hard Negatives): 3
- Missing Labels: 0

## Issues Found & Action Taken
- Sequence Leakage Fixed (Moved to consistent splits): 36 frames
- Exact Duplicates Automatically Fixed: 0
- Invalid Boxes Removed/Flagged: 0
- Suspicious Small Boxes Flagged for Review: 0
- High IoU Duplicate Boxes Flagged for Review: 6

## Next Steps
- Review images and labels in the `review/manual-label-review/` directory inside the new dataset folder.
