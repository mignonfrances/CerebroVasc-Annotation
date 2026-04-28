import os
import json
import tkinter as tk
from tkinter import filedialog
import numpy as np
import pydicom
from PIL import Image, ImageTk
from datetime import datetime

class DicomViewer:
    def __init__(self, root):
        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True)

        # Canvas (center / main area)
        self.canvas = tk.Canvas(main_frame, width=512, height=512, cursor="cross")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Configure>", self.on_resize)

        # Small legend on right
        legend_frame = tk.Frame(main_frame, width=220)
        legend_frame.pack(side="right", fill="y")
        # legend_frame.pack_propagate(False)

        self.class_info = {
            1: ("Cortical vessel", "green"),
            2: ("Surface vessel", "yellow"),
            3: ("Indistinguishable blush", "magenta"),
            4: ("No vessel/s (hard)", "blue"),
            5: ("No vessel/s (easy)", "cyan")
        }

        tk.Label(legend_frame, text="Classes", font=("Arial", 12, "bold")).pack(anchor="w")

        for k, (name, color) in self.class_info.items():
            row = tk.Frame(legend_frame)
            row.pack(anchor="w", pady=2)

            swatch = tk.Canvas(row, width=12, height=12)
            swatch.create_rectangle(0, 0, 12, 12, fill=color)
            swatch.pack(side="left")

            tk.Label(row, font=("Arial", 8), text=f"{k} - {name}").pack(side="left", padx=5)

        self.selected_class_var = tk.StringVar(value="Selected: 1 - Vessel/s (easy)")
        tk.Label(legend_frame, textvariable=self.selected_class_var, font=("Arial", 9, "bold"), anchor="w",
                 justify="left").pack(anchor="w", pady=(6, 4))

        self.class_cont = {
            "Pan Up": "W",
            "Pan Down": "S",
            "Pan Left": "A",
            "Pan Right": "D",
            "Zoom In": "E or Ctrl+Scroll ↑",
            "Zoom Out": "Q or Ctrl+Scroll ↓",
            "Next Slice": "Z or Scroll ↑",
            "Prev Slice": "C or Scroll ↓",
            "Start polygon": "Left Click",
            "End polygon": "Right Click",
            "Undo": "X or Ctrl+Z"
        }

        tk.Label(legend_frame, text="Controls", font=("Arial", 12, "bold")).pack(anchor="w")

        for act, key in self.class_cont.items():
            row = tk.Frame(legend_frame)
            row.pack(anchor="w", fill="x", pady=1)

            tk.Label(row, text=act, width=10, font=("Arial", 8, "bold"), anchor="e").grid(row=0, column=0, sticky="w")
            # tk.Label(row, text=":", width=1).grid(row=0, column=1)
            tk.Label(row, text=key, width=10, font=("Arial", 8), anchor="w").grid(row=0, column=2, sticky="w", padx=5)

        self.root = root
        self.root.title("DICOM Viewer")

        # Slider
        # self.slider = tk.Scale(root, from_=0, to=0, orient=tk.HORIZONTAL,
        #                        command=self.update_slice, label="Slice")
        # self.slider.pack(fill="x")

        slider_frame = tk.Frame(root)
        slider_frame.pack(fill="x")

        tk.Button(slider_frame, text="<", command=self.prev_slice, width=3).pack(side="left")

        self.slider = tk.Scale(
            slider_frame,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            command=self.update_slice
        )
        self.slider.pack(side="left", fill="x", expand=True)

        tk.Button(slider_frame, text=">", command=self.next_slice, width=3).pack(side="left")

        self.current_folder = "Unknown"

        self.scale = 1.5
        self.min_scale = 0.2
        self.max_scale = 8.0
        self.offset_x = 0
        self.offset_y = 0

        self.images = []
        self.tk_img = None
        self.current_slice = 0

        self._drag_start = None

        # Labels
        self.root.bind("1", lambda e: self.set_current_label(1))
        self.root.bind("2", lambda e: self.set_current_label(2))
        self.root.bind("3", lambda e: self.set_current_label(3))
        self.root.bind("4", lambda e: self.set_current_label(4))
        self.root.bind("5", lambda e: self.set_current_label(5))
        self.set_current_label(1)

        # polygon selection
        self.start_x = self.start_y = None
        self.rect = None
        self.annotations = {}  # {slice_idx: [ [ (x,y), (x,y), ... ], ... ]}
        self.current_polygon = []
        self.temp_line = None

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<Button-3>", self.finish_polygon)

        # bind arrow keys
        self.root.bind("<w>", self.pan_up)
        self.root.bind("<s>", self.pan_down)
        self.root.bind("<a>", self.pan_left)
        self.root.bind("<d>", self.pan_right)

        # zoom
        self.root.bind("<e>", self.zoom_in)
        self.root.bind("<q>", self.zoom_out)

        # move across slides with mouse wheel
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mousewheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mousewheel)  # Linux scroll down

        # Undo
        self.root.bind("<x>", self.undo_last)
        self.root.bind("<Control-z>", self.undo_last)

        # Buttons LAST
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="Open Folder", command=self.load_folder).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Undo", command=self.undo_last).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Copy last area from previous slice", command=self.copy_last_polygon).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Copy last area from next slice", command=self.copy_next_polygon).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Zoom In (+)", command=self.zoom_in).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Zoom Out (-)", command=self.zoom_out).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reset View", command=self.reset_view).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save Boxes (JSON)", command=self.save_json).pack(side="left", padx=5)

        # self.label_var = tk.StringVar(value="0")

        # tk.Entry(btn_frame, textvariable=self.label_var, width=5).pack(side="left")

    def set_current_label(self, label):
        self.current_label = label
        class_name = self.class_info.get(label, ("Unknown", ""))[0]
        self.selected_class_var.set(f"Selected: {label} - {class_name}")

    def prev_slice(self):
        if self.current_slice > 0:
            self.current_slice -= 1
            self.slider.set(self.current_slice)

    def next_slice(self):
        if self.current_slice < len(self.images) - 1:
            self.current_slice += 1
            self.slider.set(self.current_slice)

    def on_mousewheel(self, event):
        if hasattr(event, "delta"):  # Windows / macOS
            if event.delta > 0:
                self.next_slice()
            else:
                self.prev_slice()
        else:  # Linux
            if event.num == 4:
                self.next_slice()
            elif event.num == 5:
                self.prev_slice()

    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.current_folder = os.path.basename(folder)  # Add this line

        files = [os.path.join(folder, f) for f in os.listdir(folder)]

        dicoms = []
        for f in files:
            try:
                d = pydicom.dcmread(f)
                dicoms.append(d)
            except:
                pass

        # sort by instance number if available
        dicoms.sort(key=lambda x: getattr(x, "InstanceNumber", 0))

        self.images = []

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.slider.config(to=len(self.images) - 1)
        self.slider.set(0)
        self.update_slice(0)

        def apply_window(d):
            img = d.pixel_array.astype(np.float32)

            wc = getattr(d, "WindowCenter", None)
            ww = getattr(d, "WindowWidth", None)

            if wc is not None and ww is not None:
                if isinstance(wc, pydicom.multival.MultiValue):
                    wc = wc[0]
                if isinstance(ww, pydicom.multival.MultiValue):
                    ww = ww[0]

                low = wc - ww / 2
                high = wc + ww / 2

                img = np.clip(img, low, high)
                img = (img - low) / (high - low) * 255.0
            else:
                img = (img - img.min()) / (img.max() - img.min() + 1e-8) * 255.0

            return img.astype(np.uint8)

        for d in dicoms:
            img = apply_window(d)
            self.images.append(img)

        self.slider.config(to=len(self.images) - 1)
        self.slider.set(0)
        self.update_slice(0)

    def update_center(self):
        self.center_x = self.canvas.winfo_width() / 2 + self.offset_x
        self.center_y = self.canvas.winfo_height() / 2 + self.offset_y

    def draw_image(self):
        if self.tk_img is None:
            return

        self.canvas.delete("all")

        self.update_center()

        self.canvas.create_image(
            self.center_x,
            self.center_y,
            image=self.tk_img,
            anchor="center"
        )

        self.draw_polygons()

    def update_slice(self, val):
        if not self.images:
            return

        self.current_slice = int(val)
        img = self.images[self.current_slice]

        h, w = img.shape

        disp = Image.fromarray(img).resize(
            (int(w * self.scale), int(h * self.scale))
        )

        self.tk_img = ImageTk.PhotoImage(disp)

        self.draw_image()

    def draw_polygons(self):
        polys = self.annotations.get(self.current_slice, [])

        for poly, label in polys:
            coords = []
            for x, y in poly:
                cx, cy = self.image_to_canvas(x, y)
                coords.extend([cx, cy])

            color = self.class_info.get(label, ("", "red"))[1]

            self.canvas.create_polygon(
                coords,
                outline=color,
                fill="",
                width=2
            )

    def image_to_canvas(self, x, y):
        img_h, img_w = self.images[self.current_slice].shape

        sx = (x - img_w / 2) * self.scale
        sy = (y - img_h / 2) * self.scale

        cx = self.center_x + sx
        cy = self.center_y + sy

        return cx, cy

    def on_resize(self, event):
        self.draw_image()

    def on_scroll(self, event):
        if not self.images:
            return

        if hasattr(event, "delta"):
            step = 1 if event.delta > 0 else -1
        else:
            step = 1 if event.num == 4 else -1

        new_idx = self.current_slice + step
        new_idx = max(0, min(len(self.images) - 1, new_idx))

        self.slider.set(new_idx)
        self.update_slice(new_idx)

    def pan_up(self, event):
        self.offset_y += 20
        self.draw_image()

    def pan_down(self, event):
        self.offset_y -= 20
        self.draw_image()

    def pan_left(self, event):
        self.offset_x += 20
        self.draw_image()

    def pan_right(self, event):
        self.offset_x -= 20
        self.draw_image()

    def reset_view(self):
        self.scale = 1.5
        self.offset_x = 0
        self.offset_y = 0

        self.update_slice(self.current_slice)

    def canvas_to_image(self, cx, cy):
        img_h, img_w = self.images[self.current_slice].shape

        x = (cx - self.center_x) / self.scale + img_w / 2
        y = (cy - self.center_y) / self.scale + img_h / 2

        return x, y

    def on_click(self, event):
        x, y = self.canvas_to_image(event.x, event.y)
        self.current_polygon.append((x, y))

        r = 2
        self.canvas.create_oval(event.x - r, event.y - r,
                                event.x + r, event.y + r,
                                fill="yellow")

        if len(self.current_polygon) > 1:
            x1, y1 = self.current_polygon[-2]
            x2, y2 = self.current_polygon[-1]

            c1 = self.image_to_canvas(x1, y1)
            c2 = self.image_to_canvas(x2, y2)

            self.canvas.create_line(*c1, *c2, fill="red", width=2, dash=(1, 3))

    def on_move(self, event):
        if not self.current_polygon:
            return

        if self.temp_line:
            self.canvas.delete(self.temp_line)

        x1, y1 = self.current_polygon[-1]
        c1 = self.image_to_canvas(x1, y1)

        self.temp_line = self.canvas.create_line(
            c1[0], c1[1],
            event.x, event.y,
            fill="gray", dash=(2, 2)
        )

    def finish_polygon(self, event=None):
        if len(self.current_polygon) < 3:
            self.current_polygon = []
            return

        s = self.current_slice
        if s not in self.annotations:
            self.annotations[s] = []

        self.annotations[s].append(
            (self.current_polygon.copy(), self.current_label)
        )

        self.current_polygon = []

        if self.temp_line:
            self.canvas.delete(self.temp_line)
            self.temp_line = None

        self.update_slice(self.current_slice)


    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y,
                                                 event.x, event.y,
                                                 outline="green")

    def on_drag(self, event):
        if self.rect:
            self.canvas.coords(self.rect,
                               self.start_x, self.start_y,
                               event.x, event.y)

    def on_release(self, event):
        if self.rect:
            # convert from zoomed coords → base coords
            x1 = (self.start_x - self.x_offset) / self.zoom
            y1 = (self.start_y - self.y_offset) / self.zoom
            x2 = (event.x - self.x_offset) / self.zoom
            y2 = (event.y - self.y_offset) / self.zoom

            self.boxes.append({
                "x1": int(x1), "y1": int(y1),
                "x2": int(x2), "y2": int(y2)
            })

            self.rect = None
            self.update_slice(self.current_slice)

    def undo_last(self, event=None):
        s = self.current_slice
        if s in self.annotations and self.annotations[s]:
            self.annotations[s].pop()
        self.update_slice(self.current_slice)

    def copy_last_polygon(self):
        if self.current_slice == 0:
            return

        prev_slice = self.current_slice - 1

        if prev_slice not in self.annotations:
            return
        if not self.annotations[prev_slice]:
            return

        last_poly, label = self.annotations[prev_slice][-1]

        if self.current_slice not in self.annotations:
            self.annotations[self.current_slice] = []

        self.annotations[self.current_slice].append(
            (last_poly.copy(), label)
        )

        self.update_slice(self.current_slice)

    def copy_next_polygon(self):
        next_slice = self.current_slice + 1

        if next_slice not in self.annotations:
            return
        if not self.annotations[next_slice]:
            return

        next_poly, label = self.annotations[next_slice][-1]

        if self.current_slice not in self.annotations:
            self.annotations[self.current_slice] = []

        self.annotations[self.current_slice].append(
            (next_poly.copy(), label)
        )

        self.update_slice(self.current_slice)

    def on_zoom(self, event):
        factor = 1.1 if getattr(event, "delta", 0) > 0 or getattr(event, "num", None) == 4 else 0.9

        new_scale = max(self.min_scale, min(self.max_scale, self.scale * factor))

        self.scale = new_scale
        self.draw_image()

    def zoom_in(self, event=None):
        self.scale *= 1.25
        self.update_slice(self.current_slice)

    def zoom_out(self, event=None):
        self.scale /= 1.25
        self.update_slice(self.current_slice)

    def start_pan(self, event):
        self._drag_start = (event.x, event.y)

    def do_pan(self, event):
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]

        self.offset_x += dx
        self.offset_y += dy

        self._drag_start = (event.x, event.y)

        self.draw_image()

    def save_json(self):
        # Generate filename with date, time, and folder name
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        folder_name = getattr(self, "current_folder", "Unknown")

        filename = f"{folder_name}_{date_str}_{time_str}.json"

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=filename,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        export = {
            "timestamp": now.isoformat(),
            "date": date_str,
            "time": time_str,
            "folder_name": folder_name,
            "image_count": len(self.images),
            "annotations": {}
        }

        for slice_idx, polys in self.annotations.items():
            export["annotations"][slice_idx] = [
                {
                    "label": int(label),
                    "points": [[float(x), float(y)] for (x, y) in poly]
                }
                for poly, label in polys
            ]

        with open(path, "w") as f:
            json.dump(export, f, indent=2)

if __name__ == "__main__":
    root = tk.Tk()
    app = DicomViewer(root)
    root.mainloop()