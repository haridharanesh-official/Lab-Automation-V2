import cv2
import json
import os
import glob
import numpy as np

CONFIG_FILE = r"C:\Users\prith\Downloads\Lab Automation v2.0\config\zones.json"
DATASET_DIR = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean\images\train"
OUTPUT_DIR = r"C:\Users\prith\Downloads\Lab Automation v2.0\docs\validation"

class ZoneValidator:
    def __init__(self):
        self.zones = []
        self.load_zones()
        self.bg_image = self._get_latest_empty_frame()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _get_latest_empty_frame(self):
        search_pattern = os.path.join(DATASET_DIR, "hardneg_*.jpg")
        files = glob.glob(search_pattern)
        if not files:
            return np.zeros((720, 1280, 3), dtype=np.uint8)
        files.sort(key=os.path.getmtime)
        return cv2.imread(files[-1])

    def load_zones(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                if 'zones' in data:
                    self.zones = data['zones']

    def point_in_zone(self, x, y):
        for i, zone_pts in enumerate(self.zones):
            if len(zone_pts) > 2:
                pts = np.array(zone_pts, np.int32)
                if cv2.pointPolygonTest(pts, (x, y), False) >= 0:
                    return i + 1
        return None

    def draw_zones(self, img):
        colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255), (255, 255, 0)]
        for i, zone_pts in enumerate(self.zones):
            if len(zone_pts) > 2:
                pts = np.array(zone_pts, np.int32).reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, colors[i], 2)
        return img

    def simulate_person(self, img, box_center, box_w, box_h, label):
        x, y = box_center
        # Bounding box coordinates
        x1, y1 = int(x - box_w / 2), int(y - box_h / 2)
        x2, y2 = int(x + box_w / 2), int(y + box_h / 2)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 2)
        
        # Bottom center point
        bx, by = int(x), int(y2)
        cv2.circle(img, (bx, by), 5, (0, 0, 255), -1)
        
        assigned_zone = self.point_in_zone(bx, by)
        zone_str = f"Z{assigned_zone}" if assigned_zone else "None"
        
        text = f"{label} -> {zone_str}"
        cv2.putText(img, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def validate_centers(self):
        img = self.bg_image.copy()
        img = self.draw_zones(img)
        for i, zone_pts in enumerate(self.zones):
            if len(zone_pts) > 2:
                pts = np.array(zone_pts, np.int32)
                M = cv2.moments(pts)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    
                    # Assume bottom center is at cX, cY. Person box is slightly above
                    box_h = 100
                    box_w = 40
                    center_y = cY - box_h // 2
                    self.simulate_person(img, (cX, center_y), box_w, box_h, f"Center Z{i+1}")
                    
        out_path = os.path.join(OUTPUT_DIR, "validation_centers.jpg")
        cv2.imwrite(out_path, img)
        print(f"Saved {out_path}")

    def validate_scenarios(self):
        # We simulate people at arbitrary points for these tests since we only have empty lab background
        # Or we can ask user to provide images with people. Since we only have empty frame:
        
        # Seated person (shorter box)
        img = self.bg_image.copy()
        img = self.draw_zones(img)
        self.simulate_person(img, (400, 500), 60, 60, "Seated")
        out_path = os.path.join(OUTPUT_DIR, "validation_seated.jpg")
        cv2.imwrite(out_path, img)
        print(f"Saved {out_path}")

        # Door area
        img = self.bg_image.copy()
        img = self.draw_zones(img)
        self.simulate_person(img, (100, 300), 50, 150, "Door")
        out_path = os.path.join(OUTPUT_DIR, "validation_door.jpg")
        cv2.imwrite(out_path, img)
        print(f"Saved {out_path}")
        
        # Boundaries
        img = self.bg_image.copy()
        img = self.draw_zones(img)
        self.simulate_person(img, (426, 360), 40, 100, "Boundary")
        out_path = os.path.join(OUTPUT_DIR, "validation_boundary.jpg")
        cv2.imwrite(out_path, img)
        print(f"Saved {out_path}")

    def run(self):
        self.validate_centers()
        self.validate_scenarios()
        print("Validation images generated.")

if __name__ == '__main__':
    v = ZoneValidator()
    v.run()
