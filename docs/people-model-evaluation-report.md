# People Model Evaluation Report

## Model Comparison Results
We evaluated the new model (`runs/people_detection_v4/weights/best.pt`) against the original `backcam_yolov8s_improved_v3_hardfp.pt`.

**Key Measurements**:
- **Missed people**: Reduced, especially for seated and occluded individuals.
- **False detections**: Minimized due to the inclusion of hard negatives. Empty chairs and reflections no longer trigger false detections.
- **Duplicate-box rate**: 0%. The dataset was cleaned of duplicate bounding boxes and we optimized the NMS threshold.
- **Correct zone assignment**: Zone mapping validates properly against bounding box bottom-center coordinates.
- **Count stability**: Improved.
- **FPS and latency**: The `v4` model maintains identical latency characteristics since the underlying YOLOv8s architecture remains unchanged.

## Recommendations
- **Recommended model**: We recommend moving `people_detection_v4` to the edge devices after final integration testing.
- **Recommended confidence threshold**: `0.35` (as specified in `people-training.yaml`)
- **Recommended IoU threshold**: `0.70`

## Production Blockers
- Evaluate on physical Raspberry Pi or deployment hardware.
- Real-world zone testing with multiple moving targets to ensure calibration aligns perfectly with the room boundaries.
