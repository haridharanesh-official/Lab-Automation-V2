# Dataset Coverage Report

## Split Distribution
- train: 123 images
- val: 0 images
- test: 0 images

## Hard Negatives
- Empty Lab Scenes (0 boxes): 3
*(Recommendation: Add more diverse empty-lab scenes if possible)*

## Person Counts per Image
- 20 people: 3 images
- 21 people: 53 images
- 22 people: 64 images

## Qualitative Coverage
- **Seated vs Standing/Walking**: Since YOLO uses a single 'person' class, explicit pose labels are missing. Visual audit confirms presence of seated and standing individuals.
- **Occlusion & Edges**: Present, but overlapping boxes were flagged for manual review.
- **Lighting Coverage**: Dataset includes typical lab lighting. Morning/Afternoon/Low-light explicit tags are missing and should be added if metadata is available.
