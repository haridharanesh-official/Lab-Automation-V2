import os
import glob
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw

DATASET_PATH = r"C:\Users\prith\Downloads\Lab automation\LabVision-AI\datasets\labos_backcam_people_v4_clean"
REVIEW_DIR = os.path.join(DATASET_PATH, "review", "manual-label-review")

class LabelReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Manual Label Review Tool")
        
        self.image_files = glob.glob(os.path.join(REVIEW_DIR, '*.jpg'))
        self.current_idx = 0
        
        self.canvas = tk.Canvas(root, width=1280, height=720)
        self.canvas.pack()
        
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(self.btn_frame, text="Save & Next", command=self.save_and_next).pack(side=tk.LEFT, padx=5)
        tk.Button(self.btn_frame, text="Skip", command=self.skip).pack(side=tk.LEFT, padx=5)
        tk.Label(self.btn_frame, text="Click on a box to toggle keep/delete").pack(side=tk.LEFT, padx=20)
        
        self.canvas.bind("<Button-1>", self.on_click)
        
        self.boxes = []
        self.img = None
        self.tk_img = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        self.load_image()

    def load_image(self):
        if self.current_idx >= len(self.image_files):
            messagebox.showinfo("Done", "All images reviewed!")
            self.root.quit()
            return
            
        img_path = self.image_files[self.current_idx]
        lbl_path = os.path.splitext(img_path)[0] + '.txt'
        
        self.img = Image.open(img_path)
        w, h = self.img.size
        
        self.scale_x = 1280 / w
        self.scale_y = 720 / h
        
        resized = self.img.resize((1280, 720))
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        self.boxes = []
        if os.path.exists(lbl_path):
            with open(lbl_path, 'r') as f:
                for line in f.readlines():
                    parts = line.strip().split()
                    if len(parts) == 5:
                        c, x, y, bw, bh = map(float, parts)
                        # State 1 = keep, 0 = delete
                        self.boxes.append({'class': int(c), 'x': x, 'y': y, 'w': bw, 'h': bh, 'state': 1, 'line': line})
                        
        self.draw_boxes()

    def draw_boxes(self):
        self.canvas.delete("box")
        for i, box in enumerate(self.boxes):
            x1 = (box['x'] - box['w']/2) * 1280
            y1 = (box['y'] - box['h']/2) * 720
            x2 = (box['x'] + box['w']/2) * 1280
            y2 = (box['y'] + box['h']/2) * 720
            
            color = "green" if box['state'] == 1 else "red"
            stipple = "" if box['state'] == 1 else "gray50"
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, tags="box", stipple=stipple)
            self.canvas.create_text(x1 + 10, max(10, y1 - 10), text=f"ID:{i}", fill=color, tags="box")

    def on_click(self, event):
        x_norm = event.x / 1280
        y_norm = event.y / 720
        
        for box in self.boxes:
            x1 = box['x'] - box['w']/2
            y1 = box['y'] - box['h']/2
            x2 = box['x'] + box['w']/2
            y2 = box['y'] + box['h']/2
            
            if x1 <= x_norm <= x2 and y1 <= y_norm <= y2:
                box['state'] = 1 - box['state']
                break
                
        self.draw_boxes()

    def save_and_next(self):
        img_path = self.image_files[self.current_idx]
        filename = os.path.basename(img_path)
        lbl_name = os.path.splitext(filename)[0] + '.txt'
        
        # Save to the main clean dataset directory
        main_img_path = None
        main_lbl_path = None
        for split in ['train', 'val', 'test']:
            if os.path.exists(os.path.join(DATASET_PATH, 'images', split, filename)):
                main_img_path = os.path.join(DATASET_PATH, 'images', split, filename)
                main_lbl_path = os.path.join(DATASET_PATH, 'labels', split, lbl_name)
                break
                
        if main_lbl_path:
            with open(main_lbl_path, 'w') as f:
                for box in self.boxes:
                    if box['state'] == 1:
                        f.write(box['line'])
                        
            print(f"Saved {filename} to {main_lbl_path}")
            
        self.current_idx += 1
        self.load_image()

    def skip(self):
        self.current_idx += 1
        self.load_image()

if __name__ == "__main__":
    root = tk.Tk()
    app = LabelReviewApp(root)
    root.mainloop()
