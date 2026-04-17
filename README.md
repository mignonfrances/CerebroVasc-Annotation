# DICOM Viewer with Annotation (Tkinter)

## Overview

Python GUI for viewing DICOM image stacks with basic annotation tools. Supports slice navigation, zooming, polygonal ROI selection, and JSON export of annotations.

---

## Features

* Load a folder of DICOM files (auto-sorted by `InstanceNumber`)
* Indicate annotation classes

```0: ("No vessel/s (easy to spot)", "red"),
   1: ("Vessel/s (easy to spot)", "green"),
   2: ("No vessel/s (hard to spot)", "blue"),
   3: ("Vessel/s (hard to spot)", "yellow")
```

* Scroll through slices using a slider
* Zoom in/out
* Draw polygonal regions of interest (ROIs)
* Undo last annotation
* Export annotations to JSON

---

## Requirements

* Python 3.8+
* Dependencies listed in `requirements.txt`

---

## Setup (Recommended)

Create an isolated environment to avoid dependency conflicts.

Note: Run the following using **Command Prompt** (Windows) or **Terminal** (macOS/Linux)

### Windows

```cmd
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Running the Application

### Windows

```cmd
python AnnotationTool.py
```

### macOS / Linux

```bash
python3 AnnotationTool.py
```

---

## Additional Notes

* If `python` does not work on macOS/Linux, use `python3`.
* To deactivate the virtual environment:

  ```bash
  deactivate
  ```
* If you encounter permission issues on macOS/Linux:

  ```bash
  chmod +x AnnotationTool.py
  ```

---

## Optional (DICOM Support Troubleshooting)

If DICOM files fail to load:

```bash
pip install pydicom numpy pillow
```
---

### Workflow

1. Click **Open Folder** and select a directory containing a DICOM file series
2. Use **Page Up/Page Down** or **Scroll Up/Down** to navigate between slices
3. Use **Zoom In / Zoom Out** as needed
4. Pan across the images using **arrow keys** as needed
5. Select the area class using keys **0**, **1**, **2**, and **3**.
6. Start your polygon area by **left-clicking** on the desired starting point
7. Drag to the next vertex point and set once again using the left click button
8. Use the **right-click** button to close the polygon and end the selection
9. Use the **Copy last area from previous slice** and **Copy last area from next slice** buttons to copy the most recent selections from the immediate previous and next slices, respectively
10. Click **Undo Last Box** to remove the most recent annotation (Note: this only applies to the current slice)
11. Click **Save Boxes (JSON)** to export annotations

---

## Output Format

Annotations are saved as a JSON list:

```{
  "image_count": 176,
  "annotations": {
    "0": [
      {
        "label": 0,
        "points": [
          [
            122.9668352,
            113.2150784
          ],
          [
            130.3068672,
            114.26365440000001
          ],
          [
            128.0,
            121.8134016
          ],
          [
            122.75712,
            120.5551104
          ],
          [
            117.9336704,
            113.844224
          ]
        ]
      },
      {
        "label": 1,
        "points": [
          [
            107.02848,
            129.1534336
          ],
          [
            114.368512,
            125.5882752
          ],
          [
            116.2559488,
            131.2505856
          ],
          [
            109.9644928,
            135.6546048
          ]
        ]
      }
    ],
    "9": [
      {
        "label": 1,
        "points": [
          [
            116.8850944,
            108.3916288
          ],
          [
            125.6931328,
            102.7293184
          ],
          [
            131.9845888,
            110.698496
          ],
          [
            130.5165824,
            119.087104
          ],
          [
            120.8696832,
            118.8773888
          ],
          [
            116.465664,
            113.0053632
          ]
        ]
      }
    ],
    "10": [
      {
        "label": 1,
        "points": [
          [
            116.8850944,
            108.3916288
          ],
          [
            125.6931328,
            102.7293184
          ],
          [
            131.9845888,
            110.698496
          ],
          [
            130.5165824,
            119.087104
          ],
          [
            120.8696832,
            118.8773888
          ],
          [
            116.465664,
            113.0053632
          ]
        ]
      }
    ],
    "14": [
      {
        "label": 3,
        "points": [
          [
            111.6422144,
            134.3963136
          ],
          [
            129.048576,
            124.9591296
          ],
          [
            134.5011712,
            144.0432128
          ],
          [
            112.27136,
            160.4009984
          ]
        ]
      }
    ]
  }
}
```

Coordinates are stored in the original (unzoomed) image space.

