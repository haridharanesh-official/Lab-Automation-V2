import cv2
import json
import os
import glob
import numpy as np

CONFIG_FILE = r"C:\Users\prith\Downloads\Lab Automation v2.0\config\zones.json"
DATASET_DIR = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean\images\train"

class RoomMapper:
    def __init__(self):
        self.zones = [[] for _ in range(6)]
        self.current_zone = 0
        self.bg_image = self._get_latest_empty_frame()
        self.test_mode = False

    def _get_latest_empty_frame(self):
        # We find a hard negative frame which should be empty
        search_pattern = os.path.join(DATASET_DIR, "hardneg_*.jpg")
        files = glob.glob(search_pattern)
        if not files:
            # fallback to blank image
            print("Warning: No hard negative found. Using blank image.")
            return np.zeros((720, 1280, 3), dtype=np.uint8)
        files.sort(key=os.path.getmtime)
        return cv2.imread(files[-1])

    def load_zones(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                if 'zones' in data:
                    self.zones = data['zones']

    def save_zones(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        data = {
            "note": "Provisional mapping. Needs real person-position tests to confirm.",
            "zones": self.zones
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Zones saved to {CONFIG_FILE}")

    def point_in_zone(self, x, y):
        for i, zone_pts in enumerate(self.zones):
            if len(zone_pts) > 2:
                pts = np.array(zone_pts, np.int32)
                if cv2.pointPolygonTest(pts, (x, y), False) >= 0:
                    return i + 1
        return None

    def draw(self, event, x, y, flags, param):
        if self.test_mode:
            if event == cv2.EVENT_LBUTTONDOWN:
                zone_idx = self.point_in_zone(x, y)
                if zone_idx:
                    print(f"Point ({x}, {y}) is in Zone {zone_idx}")
                else:
                    print(f"Point ({x}, {y}) is NOT in any zone.")
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            if self.current_zone < 6:
                self.zones[self.current_zone].append([x, y])

    def run(self):
        self.load_zones()
        cv2.namedWindow('Room Mapper')
        cv2.setMouseCallback('Room Mapper', self.draw)

        while True:
            display = self.bg_image.copy()

            # Draw existing zones
            colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255), (255, 255, 0)]
            for i, zone_pts in enumerate(self.zones):
                if len(zone_pts) > 0:
                    pts = np.array(zone_pts, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(display, [pts], True, colors[i], 2)
                    # Label
                    M = cv2.moments(pts)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        cv2.putText(display, f"Zone {i+1}", (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)

            mode_text = "TEST MODE (Click to test)" if self.test_mode else f"EDIT MODE (Zone {self.current_zone + 1})"
            cv2.putText(display, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display, "Keys: 1-6: Select Zone, c: Clear Zone, s: Save, t: Toggle Test Mode, q: Quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow('Room Mapper', display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('s'):
                self.save_zones()
            elif key == ord('t'):
                self.test_mode = not self.test_mode
            elif key == ord('c'):
                self.zones[self.current_zone] = []
            elif ord('1') <= key <= ord('6'):
                self.current_zone = key - ord('1')

        cv2.destroyAllWindows()

if __name__ == '__main__':
    mapper = RoomMapper()
    mapper.run()
