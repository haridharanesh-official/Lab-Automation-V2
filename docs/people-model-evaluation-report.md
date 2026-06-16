# People Model Evaluation Report

## Evaluation Results
The candidate model (`runs/people_detection_v4-2/weights/best.pt`) was evaluated against the production model (`models/backcam_yolov8s_improved_v3_hardfp.pt`).

**Settings used:**
- Confidence: 0.35
- IoU: 0.70
- Image size: 1280
- Device: CPU (Fallback)
- Tracker: ByteTrack

**Metrics:**
- **Model A (v3) Latency:** 128.18ms
- **Model B (v4) Latency:** 110.12ms (14% Faster)
- **Model A Count Flicker Score:** 0
- **Model B Count Flicker Score:** 0

**Specific Checks:**
- **Duplicate boxes:** Cleaned in the dataset, effectively mitigating double-counting.
- **False detections:** The new model utilized hard negatives (empty lab) reducing false detections on chairs and monitors.
- **Crowded Scenes / Occlusions:** 6 uncertain samples were processed side-by-side for human review.

## Conclusion
The candidate model demonstrates equal tracking stability (0 flicker) while operating at lower latency. However, until the manual review of the 6 crowded samples explicitly confirms that the candidate model *clearly beats* the existing model, we are keeping the current custom model in the runtime configuration.
