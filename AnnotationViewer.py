import os
import json
import tkinter as tk
from tkinter import filedialog
import numpy as np
import pydicom
from PIL import Image, ImageTk


class AnnotationViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Annotation Viewer")

        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True)

        # Canvas
        self.canvas = tk.Canvas(main_frame, width=512, height=512, bg="gray")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)

        # Info panel on right
        info_frame = tk.Frame(main_frame, width=250, bg="white")
        info_frame.pack(side="right", fill="both")
        info_frame.pack_propagate(False)

        tk.Label(info_frame, text="Legend", font=("Arial", 12, "bold"), bg="white").pack(pady=10, anchor="w", padx=10)

        # Legend (class colors)
        legend_inner = tk.Frame(info_frame, bg="white")
        legend_inner.pack(padx=10, pady=5, anchor="w", fill="x")

        self.class_info = {
            1: ("Cortical vessel", "green"),
            2: ("Surface vessel", "yellow"),
            3: ("Indistinguishable blush", "magenta"),
            4: ("No vessel/s (hard)", "blue"),
            5: ("No vessel/s (easy)", "cyan")
        }

        for k, (name, color) in self.class_info.items():
            row = tk.Frame(legend_inner, bg="white")
            row.pack(anchor="w", pady=2)

            swatch = tk.Canvas(row, width=12, height=12, bg="white", highlightthickness=0)
            swatch.create_rectangle(0, 0, 12, 12, fill=color, outline="black")
            swatch.pack(side="left", padx=5)

            tk.Label(row, text=f"{k} - {name}", font=("Arial", 8), bg="white").pack(side="left")

        tk.Label(info_frame, text="Slice Info", font=("Arial", 12, "bold"), bg="white").pack(pady=(10, 5), anchor="w",
                                                                                             padx=10)

        self.info_text = tk.Text(info_frame, height=15, width=30, font=("Arial", 9))
        self.info_text.pack(padx=10, pady=5, fill="both", expand=True)

        # Controls frame
        ctrl_frame = tk.Frame(root)
        ctrl_frame.pack(fill="x", pady=5)

        tk.Button(ctrl_frame, text="Load JSON", command=self.load_json).pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="< Prev", command=self.prev_slice).pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="Next >", command=self.next_slice).pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="Zoom In (+)", command=self.zoom_in).pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="Zoom Out (-)", command=self.zoom_out).pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="Reset View", command=self.reset_view).pack(side="left", padx=5)

        # Slider
        slider_frame = tk.Frame(root)
        slider_frame.pack(fill="x", padx=5)

        self.slider = tk.Scale(
            slider_frame,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            command=self.update_slice,
            label="Slice"
        )
        self.slider.pack(fill="x")

        self.images = []
        self.annotations = {}
        self.current_slice = 0
        self.tk_img = None
        self.image_folder = None

        # Zoom
        self.scale = 1.0
        self.min_scale = 0.2
        self.max_scale = 4.0
        self.offset_x = 0
        self.offset_y = 0

    def load_json(self):
        json_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not json_path:
            return

        # Load JSON
        with open(json_path, "r") as f:
            data = json.load(f)

        self.annotations = data.get("annotations", {})
        folder_name = data.get("folder_name", "")

        # Ask for image folder
        image_folder = filedialog.askdirectory(title=f"Select image folder for {folder_name}")
        if not image_folder:
            return

        self.image_folder = image_folder
        self.reset_view()
        self.load_images()

    def load_images(self):
        if not self.image_folder:
            return

        files = [os.path.join(self.image_folder, f) for f in os.listdir(self.image_folder)]
        dicoms = []

        for f in files:
            try:
                d = pydicom.dcmread(f)
                dicoms.append(d)
            except:
                pass

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
        self.current_slice = 0
        self.slider.set(0)
        self.display_slice()

    def display_slice(self):
        if not self.images:
            return

        img = self.images[self.current_slice]
        h, w = img.shape

        # Apply zoom
        scaled_w = int(w * self.scale)
        scaled_h = int(h * self.scale)

        pil_img = Image.fromarray(img).resize((scaled_w, scaled_h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(pil_img)

        self.canvas.delete("all")

        # Center position with offset
        center_x = self.canvas.winfo_width() / 2 + self.offset_x
        center_y = self.canvas.winfo_height() / 2 + self.offset_y

        self.canvas.create_image(center_x, center_y, image=self.tk_img, anchor="center")

        # Draw annotations for this slice
        self.draw_annotations(w, h)
        self.update_info()

    def draw_annotations(self, img_w, img_h):
        slice_str = str(self.current_slice)
        if slice_str not in self.annotations:
            return

        polys = self.annotations[slice_str]

        for poly_data in polys:
            label = poly_data.get("label", 1)
            points = poly_data.get("points", [])

            if len(points) < 2:
                continue

            color = self.class_info.get(label, ("Unknown", "white"))[1]

            # Transform points for zoom
            center_x = self.canvas.winfo_width() / 2 + self.offset_x
            center_y = self.canvas.winfo_height() / 2 + self.offset_y

            # Draw lines between points
            for i in range(len(points)):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % len(points)]

                # Scale and center
                cx1 = center_x + (x1 - img_w / 2) * self.scale
                cy1 = center_y + (y1 - img_h / 2) * self.scale
                cx2 = center_x + (x2 - img_w / 2) * self.scale
                cy2 = center_y + (y2 - img_h / 2) * self.scale

                self.canvas.create_line(cx1, cy1, cx2, cy2, fill=color, width=2)

            # Draw points
            for x, y in points:
                cx = center_x + (x - img_w / 2) * self.scale
                cy = center_y + (y - img_h / 2) * self.scale
                r = 4
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="white", width=1)

    def update_info(self):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)

        info = f"Slice: {self.current_slice + 1} / {len(self.images)}\n"
        info += f"Zoom: {self.scale:.1f}x\n\n"

        slice_str = str(self.current_slice)
        if slice_str in self.annotations:
            polys = self.annotations[slice_str]
            info += f"Annotations: {len(polys)}\n\n"

            for i, poly_data in enumerate(polys):
                label = poly_data.get("label", 1)
                class_name = self.class_info.get(label, ("Unknown", "white"))[0]
                points = poly_data.get("points", [])
                color = self.class_info.get(label, ("Unknown", "white"))[1]

                info += f"Polygon {i + 1}:\n"
                info += f"  Class: {label} - {class_name}\n"
                info += f"  Points: {len(points)}\n\n"
        else:
            info += "No annotations on this slice"

        self.info_text.insert("1.0", info)
        self.info_text.config(state=tk.DISABLED)

    def on_zoom(self, event):
        if not self.images:
            return

        if hasattr(event, "delta"):  # Windows
            factor = 1.2 if event.delta > 0 else 0.8
        else:  # Linux
            factor = 1.2 if event.num == 4 else 0.8

        new_scale = max(self.min_scale, min(self.max_scale, self.scale * factor))
        self.scale = new_scale
        self.display_slice()

    def zoom_in(self):
        if not self.images:
            return
        self.scale = min(self.max_scale, self.scale * 1.25)
        self.display_slice()

    def zoom_out(self):
        if not self.images:
            return
        self.scale = max(self.min_scale, self.scale / 1.25)
        self.display_slice()

    def reset_view(self):
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def prev_slice(self):
        if self.current_slice > 0:
            self.current_slice -= 1
            self.slider.set(self.current_slice)

    def next_slice(self):
        if self.current_slice < len(self.images) - 1:
            self.current_slice += 1
            self.slider.set(self.current_slice)

    def update_slice(self, val):
        self.current_slice = int(val)
        self.display_slice()


if __name__ == "__main__":
    root = tk.Tk()
    app = AnnotationViewer(root)
    root.mainloop()