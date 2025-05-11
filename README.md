# Traffic Monitoring System

A system that monitors traffic flow using YOLOv8, detects congestion, and controls traffic lights.

## Overview

The system detects and counts vehicles from camera or video input, analyzes data for congestion, and can automatically adjust traffic light timing to prevent congestion.

## Installation

Follow these steps to run the system:

1. Install Python 3.8+
2. Install required packages:

```bash
pip install -r requirements.txt
```

## Running

Run the system directly:

```bash
python run.py
```

Run with a video file:

```bash
python run.py --video viiddeo.mov
```

Save processed video:

```bash
python run.py --video viiddeo.mov --save-video
```

See all available options:

```bash
python run.py --help
```

## Usage

1. When started, a zone setup interface will appear.
2. Click left mouse button to select zone points.
3. Click right mouse button to finish a zone.
4. Select zone type: COUNT or SUM.
5. Press Enter to finish zone configuration.
6. Press 'c' to clear zone points.

## API

The system provides an API interface. View the API documentation at:

```
http://localhost:8000/docs
```

## License

MIT

## Authors

Developed as part of a bachelor's thesis. SEZIS, MHTS.
