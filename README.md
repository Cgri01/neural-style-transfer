# Neural Style Transfer Video

Real-time neural style transfer for webcam streams and video files. A FastAPI backend runs PyTorch style models on each frame, and a React frontend shows the original camera feed alongside the stylized output.

## Features

- **Live webcam styling** — WebSocket stream (`/ws/video_feed`) for low-latency frame-by-frame transfer
- **Multiple art styles** — Starry Night, Udnie, Rain Princess, Candy, and Mosaic (switch at runtime)
- **Temporal smoothing** — Reduces flicker between frames (EMA filter for live stream; optical flow for uploaded videos)
- **Adjustable quality** — Process size (256–640 for live, up to 1024 for batch video) and temporal filter alpha
- **Batch video API** — Upload `.mp4`, `.avi`, `.mov`, `.mkv`, or `.webm` and download a stylized result
- **GPU support** — Uses CUDA automatically when available

## Architecture



```
┌─────────────────┐     WebSocket / REST      ┌──────────────────┐
│  React Frontend │ ◄──────────────────────► │  FastAPI Backend │
│  (port 3000)    │                           │  (port 8000)     │
└─────────────────┘                           └────────┬─────────┘
                                                       │
                                              PyTorch style models
                                              (backend/models/)
```

| Layer | Stack |
|-------|--------|
| Frontend | React 19, Tailwind CSS, WebSocket + REST |
| Backend | FastAPI, Uvicorn, OpenCV, PyTorch |
| Models | Feed-forward CNNs (`StarryNightNet`, `FastStyleNet`) |

## Available Styles

| ID | Name | Recommended size |
|----|------|------------------|
| `starry_night` | Van Gogh — Starry Night | 512 |
| `udnie` | Francis Picabia — Udnie | 384 |
| `rain_princess` | Rain Princess | 384 |
| `candy` | Candy | 384 |
| `mosaic` | Mosaic | 384 |

Place the corresponding `.pth` weights under `backend/models/` (see [Model files](#model-files)).

## Prerequisites

- **Python** 3.10+ (backend)
- **Node.js** 18+ (frontend)
- **CUDA** (optional, recommended for real-time performance)
- **Webcam** (for the live UI)

## Quick Start

### 1. Model files

Download or copy pretrained weights into `backend/models/`:

- `Starry_Night_512.pth`
- `udnie.pth`
- `rain_princess.pth`
- `candy.pth`
- `mosaic.pth`

Paths are defined in `backend/app/config.py`.

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python run.py
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000). Set `REACT_APP_API_URL` if the API is not on `http://localhost:8000`.

### Docker Compose (optional)

From the project root:

```bash
docker compose up --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://localhost:8000](http://localhost:8000)

Mount `backend/models` so weights are available inside the container (configured in `docker-compose.yml`).

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/styles` | List styles and current selection |
| `POST` | `/set_style?style_id=...` | Switch active style |
| `POST` | `/process_frame` | Stylize a single image (multipart: `file`, `process_size`) |
| `POST` | `/process_video` | Stylize an uploaded video (`file`, `alpha`, `process_size`, optional `target_fps`, `return_format`) |
| `POST` | `/set_alpha?alpha=0.7` | Temporal filter strength (0.3–0.95) |
| `POST` | `/reset_filter` | Reset temporal filter state |
| `WS` | `/ws/video_feed?process_size=384` | Real-time frame in / stylized JPEG out |

## Project Structure

```
neural-style-transfer-video/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI routes & WebSocket
│   │   ├── style_transfer.py # Model loading & inference
│   │   ├── temporal_filter.py
│   │   ├── video_utils.py
│   │   └── config.py         # Styles & processing settings
│   ├── models/               # .pth weight files (not in repo)
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   └── src/                  # React UI (webcam, controls, theme)
├── docker-compose.yml
└── README.md
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `REACT_APP_API_URL` | `http://localhost:8000` | Backend URL for the React app |

Backend CLI (`python run.py`):

- `--port` — Listen port (default `8000`)
- `--host` — Bind address (default `0.0.0.0`)
- `--prod` / `--no-reload` — Production mode without auto-reload

## Performance Tips

- Use a **GPU** for usable real-time FPS; CPU works but is much slower.
- Lower **process size** (e.g. 256 or 384) to increase throughput on live streams.
- **Alpha** on the temporal filter trades stability vs. responsiveness (higher = smoother, more lag).
- For long videos, use `POST /process_video` with optical-flow temporal filtering instead of the WebSocket path.



