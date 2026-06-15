# People Model Comparison Report

Date: June 16, 2026

## Safety And Scope

- Comparison was offline on a local video file.
- No MQTT connection or publish operation occurred.
- No relay, Node-RED, Raspberry Pi, camera, or Auto-mode operation occurred.
- Both models were restricted to people-only class ID `0`.

## Tested Settings

- Source: `validation_clip.mp4`, back-camera lab footage
- Frames: 758
- Duration: 30.32 seconds at 25 FPS
- Resolution: 1280 x 720
- Confidence: 0.35
- Image size: 1280
- Device: CUDA 0, NVIDIA GeForce RTX 5070
- Tracker: ByteTrack
- Zones: current `config/zones.json` initial approximations

## Results

| Metric | Custom YOLOv8s | YOLO11s |
|---|---:|---:|
| Average processing FPS | 57.97 | 56.61 |
| Average inference latency | 12.39 ms | 12.99 ms |
| P95 inference latency | 13.07 ms | 14.92 ms |
| Peak allocated GPU memory | 188.83 MB | 270.25 MB |
| Mean detected people/frame | 1.253 | 0.274 |
| Maximum detected people/frame | 4 | 1 |
| Frames with one or more people | 721 / 758 | 208 / 758 |
| Frames with two or more people | 215 / 758 | 0 / 758 |
| Count changes | 50 | 60 |
| Zone-count changes | 76 | 60 |
| Unique track IDs | 11 | 4 |
| Short-lived track IDs | 5 | 2 |
| Unassigned detections | 91 | 0 |

Both models exceeded the 15 FPS requirement and completed without inference failure or CUDA instability.

## Accuracy Interpretation

No frame-level human ground-truth annotation is available for this clip. Therefore objective missed-person, false-detection, correct zone-count, seated-person, occluded-person, and true track-ID-switch scores cannot be claimed.

The same footage clearly contains multi-person periods: the custom model reported two or more people in 215 frames and up to four people, while YOLO11s never reported more than one person. YOLO11s also produced no detections in 550 frames. These results strongly indicate YOLO11s misses people in this lab view at confidence 0.35.

The custom model's 91 unassigned detections indicate the current approximate polygons do not cover every detected bottom-centre point. This is a zone-calibration issue requiring labeled visual review, not evidence that the custom detector is worse.

## Recommendation

Select `models/backcam_yolov8s_improved_v3_hardfp.pt`.

Keep confidence at `0.35` for the next labeled validation round. The custom model is faster, uses less measured GPU memory, detects multi-person scenes, and produces much stronger people coverage. Under the selection rule, YOLO11s does not demonstrate equal or better accuracy, zone counting, occlusion handling, or stability.

Do not switch the runtime model or enable Auto mode until:

- representative seated and occluded frames are labeled;
- false positives and missed people are manually scored;
- final production polygons are calibrated;
- zone-count stability is validated on longer footage.

TensorRT FP16 was not tested because accuracy validation and final zone calibration remain incomplete; optimizing before those gates would not improve the selection decision.

## Generated Files

- `comparison-results/backcam_yolov8s_improved_v3_hardfp_annotated.mp4`
- `comparison-results/yolo11s_annotated.mp4`
- `comparison-results/*_frames.csv`
- `comparison-results/*_frames.jsonl`
- `comparison-results/*_summary.json`
- `comparison-results/comparison-summary.json`

