# DICOM Viewer with Annotation (Tkinter)

## Overview

Lightweight Python GUI for viewing DICOM image stacks with basic annotation tools. Supports slice navigation, zooming, rectangular ROI selection, and JSON export of annotations.

---

## Features

* Load a folder of DICOM files (auto-sorted by `InstanceNumber`)
* Scroll through slices using a slider
* Zoom in/out
* Draw rectangular regions of interest (ROIs)
* Persistent ROI overlay across slices
* Undo last annotation
* Export annotations to JSON

---

## Requirements

* Python 3.8+
* Dependencies listed in `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

Run the script:

```bash
python your_script_name.py
```

### Workflow

1. Click **Open Folder** and select a directory containing DICOM files
2. Use the **slider** to navigate slices
3. Use **Zoom In / Zoom Out** as needed
4. Click and drag on the image to draw a box
5. Repeat to add more boxes
6. Click **Undo Last Box** to remove the most recent annotation
7. Click **Save Boxes (JSON)** to export annotations

---

## Output Format

Annotations are saved as a JSON list:

```json
[
  {
    "x1": 120,
    "y1": 80,
    "x2": 200,
    "y2": 160
  }
]
```

Coordinates are stored in the original (unzoomed) image space.

---

## Notes

* DICOM images are windowed using `WindowCenter` / `WindowWidth` when available
* Fallback normalization is applied if windowing metadata is missing
* Display is converted to 8-bit for compatibility with Tkinter
* Zoom does not currently support panning (image may be cropped when zoomed in)

---

## Limitations

* Assumes single-frame DICOM files
* No multi-series handling
* No annotation editing beyond undo
* No coordinate scaling back to original DICOM resolution (if resized)

---

## Possible Improvements

* Add pan/scroll support for zoomed images
* Support per-slice vs global annotations toggle
* Add adjustable window/level sliders
* Export annotations in image-space coordinates
* Add multi-class labeling for ROIs

