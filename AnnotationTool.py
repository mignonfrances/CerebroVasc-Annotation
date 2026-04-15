import os
import json
import tkinter as tk
from tkinter import filedialog
import numpy as np
import pydicom
from PIL import Image, ImageTk

class DicomViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("DICOM Viewer")

        # Canvas FIRST
        self.canvas = tk.Canvas(root, width=512, height=512, cursor="cross")
        self.canvas.pack()

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

        self.zoom = 1.0
        self.base_size = 512  # original display size

        self.images = []
        self.tk_img = None
        self.current_slice = 0
        self.x_offset = 0
        self.y_offset = 0

        # polygon selection
        self.start_x = self.start_y = None
        self.rect = None
        self.annotations = {}  # {slice_idx: [ [ (x,y), (x,y), ... ], ... ]}
        self.current_polygon = []
        self.temp_line = None

        # keep canvas size constant
        self.canvas.bind("<Button-1>", self.on_click)  # add point
        self.canvas.bind("<Motion>", self.on_move)  # preview line
        self.canvas.bind("<Button-3>", self.finish_polygon)  # right-click = close

        # bind arrow keys
        self.root.bind("<Left>", lambda e: self.prev_slice())
        self.root.bind("<Right>", lambda e: self.next_slice())

        # Buttons LAST
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Open Folder", command=self.load_folder).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Undo", command=self.undo_last).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Copy last area from previous slice", command=self.copy_last_polygon).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Copy last area from next slice", command=self.copy_next_polygon).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Zoom In", command=self.zoom_in).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Zoom Out", command=self.zoom_out).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save Boxes (JSON)", command=self.save_json).pack(side="left", padx=5)

    def prev_slice(self):
        if self.current_slice > 0:
            self.current_slice -= 1
            self.slider.set(self.current_slice)

    def next_slice(self):
        if self.current_slice < len(self.images) - 1:
            self.current_slice += 1
            self.slider.set(self.current_slice)

    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

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

    def update_slice(self, val):
        if not self.images:
            return

        self.current_slice = int(val)
        img = self.images[self.current_slice]

        canvas_w = 512
        canvas_h = 512

        size = max(10, int(self.base_size * self.zoom))
        pil_img = Image.fromarray(img).resize((size, size))
        self.tk_img = ImageTk.PhotoImage(pil_img)

        self.canvas.delete("all")

        self.x_offset = (canvas_w - size) // 2
        self.y_offset = (canvas_h - size) // 2

        self.canvas.create_image(self.x_offset, self.y_offset,
                                 anchor="nw", image=self.tk_img)

        polys = self.annotations.get(self.current_slice, [])
        for poly in polys:
            coords = []
            for x, y in poly:
                coords.extend([
                    x * self.zoom + self.x_offset,
                    y * self.zoom + self.y_offset
                ])
            self.canvas.create_polygon(coords, outline="red", fill="", width=2)

    def on_click(self, event):
        x = (event.x - self.x_offset) / self.zoom
        y = (event.y - self.y_offset) / self.zoom

        self.current_polygon.append((x, y))

        # draw point
        r = 2
        self.canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r, fill="yellow")

        # draw line from previous point
        if len(self.current_polygon) > 1:
            x1, y1 = self.current_polygon[-2]
            x2, y2 = self.current_polygon[-1]

            self.canvas.create_line(
                x1 * self.zoom + self.x_offset, y1 * self.zoom + self.y_offset,
                x2 * self.zoom + self.x_offset, y2 * self.zoom + self.y_offset,
                fill="green", width=2
            )

    def on_move(self, event):
        if not self.current_polygon:
            return

        if self.temp_line:
            self.canvas.delete(self.temp_line)

        x1, y1 = self.current_polygon[-1]

        self.temp_line = self.canvas.create_line(
            x1 * self.zoom + self.x_offset,
            y1 * self.zoom + self.y_offset,
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

        self.annotations[s].append(self.current_polygon.copy())
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

    def undo_last(self):
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

        last_poly = self.annotations[prev_slice][-1]

        if self.current_slice not in self.annotations:
            self.annotations[self.current_slice] = []

        # deep copy points
        new_poly = [(x, y) for x, y in last_poly]
        self.annotations[self.current_slice].append(new_poly)

        self.update_slice(self.current_slice)

    def copy_next_polygon(self):
        if self.current_slice == 0:
            return

        next_slice = self.current_slice + 1

        if next_slice not in self.annotations:
            return

        if not self.annotations[next_slice]:
            return

        last_poly_n = self.annotations[next_slice][-1]

        if self.current_slice not in self.annotations:
            self.annotations[self.current_slice] = []

        # deep copy points
        new_poly = [(x, y) for x, y in last_poly_n]
        self.annotations[self.current_slice].append(new_poly)

        self.update_slice(self.current_slice)

    def save_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return

        with open(path, "w") as f:
            json.dump(self.annotations, f, indent=2)

    def zoom_in(self):
        self.zoom *= 1.25
        self.update_slice(self.current_slice)

    def zoom_out(self):
        self.zoom /= 1.25
        self.update_slice(self.current_slice)

if __name__ == "__main__":
    root = tk.Tk()
    app = DicomViewer(root)
    root.mainloop()