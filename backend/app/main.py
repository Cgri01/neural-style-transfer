from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from app.video_utils import process_video_file, get_video_info
from app.temporal_filter import TemporalFilter , OpticalFlowFilter
from fastapi import UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse
import tempfile
import shutil
import cv2
import numpy as np
import io
import time
import base64
import asyncio
import os
import uuid

from PIL import Image

from app.style_transfer import load_style_model, apply_style, apply_style_with_fallback , get_processor
from app.video_utils import release_webcam

from app.config import (
    get_available_styles, 
    get_current_style, 
    set_current_style,
    get_style_recommended_size,
)
from app.style_transfer import get_cached_model, reload_current_style



app = FastAPI(
    title ="Neural Style Transfer API",
    description ="API for performing neural style transfer on videos and webcam streams.",
    version = "1.0.0"
)



_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
_cors_origins = (
    ["*"]
    if _cors_raw == "*"
    else [origin.strip() for origin in _cors_raw.split(",") if origin.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


_model = None
_device = None
_model_loaded = False
_temporal_filter = None
MODEL_PATH = "models/Starry_Night_512.pth"  # Model dosyasının yolu

def get_model():
    global _model, _device, _model_loaded
    
    if not _model_loaded:
        try:
            # Otomatik GPU kullanımı
            _model, _device, _ = get_cached_model() #get_cache_model'in dondurdugu style_info'yu kullanmıyoz bu yuzdende _ seklinde koyduk
            _model_loaded = True
        except Exception as e:
            print(f"Error while loading model: {e}")
            raise
    return _model, _device

def get_temporal_filter():
    """WebSocket canlı akış için TemporalFilter (alpha etkisi belirgin, hızlı)."""
    global _temporal_filter

    if _temporal_filter is None:
        _temporal_filter = TemporalFilter(alpha=0.7)
        print("Temporal filter created (realtime).")

    return _temporal_filter


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Websocket connected , Active connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Websocket disconnected. Active connections: {len(self.active_connections)}")
    
    async def send_frame(self, websocket: WebSocket, frame_bytes: bytes):
       
        try:
            await websocket.send_bytes(frame_bytes)
        except Exception as e:
            print(f"Frame send error: {e}")
            self.disconnect(websocket)
    
    async def broadcast_frame(self, frame_bytes: bytes):
       
        for connection in self.active_connections:
            try:
                await connection.send_bytes(frame_bytes)
            except Exception as e:
                print(f"Broadcast error: {e}")


# Global connection manager
manager = ConnectionManager()






#ANASAYFA
@app.get("/")
def read_root():
     return {
          "message" : "Neural Style Transfer API is working!" , 
          "status" : "online",
          "model_loaded" : _model_loaded,
          "endpoints": {
            "POST /process_frame": "Send a photo , receive stylized photo",
            "GET /health": "health check endpoint",
            "POST /reset_filter": "reset temporal filter state",
            "POST /set_alpha": "set temporal filter alpha value (0.0 to 1.0)"
        }
     }


# HEALTH CHECK ENDPOINT
@app.get("/health")
def health_check():
    
    return {
        "status": "ok",
        "service": "neural-style-transfer",
        "model_loaded": _model_loaded,
        "temporal_filter_active": _temporal_filter is not None
    }


#PROCESS FRAME ENDPOINT
@app.post("/process_frame")
async def process_frame(
    file: UploadFile = File(...),  # Frontend'den gelen resim dosyası
    process_size: int = Form(384, description="Process Size (256, 384, 512, 640)")
):

    
    # Girdi dosyasını kontrol et 
    if file is None:
        raise HTTPException(status_code=400, detail="File count not be sent")
    
    if file.filename == "":
        raise HTTPException(status_code=400, detail="File name is empty")
    
    
    try:
        
        contents = await file.read()
        
        # Bytes'ı numpy array'e çevir
        nparr = np.frombuffer(contents, np.uint8)
        
        # OpenCV ile decode et (BGR formatında)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Could not decode image file")
        
        print(f"Frame size: {frame.shape}")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File reading error: {str(e)}")
    
    
    try:
        model, device = get_model()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model error: {str(e)}")
    
    
    valid_sizes = [256, 384, 512, 640]
    if process_size not in valid_sizes:
        process_size = 384  # Varsayılan
    
    # Stil transferi uygula 
    try:
        start_time = time.time()
        styled_frame = apply_style(
            frame, model, device,
            target_size=process_size,
            use_adaptive_size=False,
            style_id=get_current_style(),
        )
        elapsed = time.time() - start_time
        print(f"Style transfer time: {elapsed:.3f} seconds")
        
        if styled_frame is None:
            raise HTTPException(status_code=500, detail="Style transfer failed")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Style transfer error: {str(e)}")
    
    # Temporal filtre uygula
    try:
        temporal_filter = get_temporal_filter()
        filtered_frame = temporal_filter.update(styled_frame)
        
    except Exception as e:
        print(f"Temporal filter error (continuing with original frame): {e}")
        filtered_frame = styled_frame  # Filtre hatasında orijinal stilize kareyi kullan
    
    # Sonucu JPEG olarak encode et
    try:
        # OpenCV formatını (BGR) JPEG'e encode et
        _, img_encoded = cv2.imencode('.jpg', filtered_frame)
        img_bytes = img_encoded.tobytes()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JPEG encode error: {str(e)}")
    
   
    return StreamingResponse(
        io.BytesIO(img_bytes),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": "inline; filename=stylized_frame.jpg",
            "X-Processing-Time": str(elapsed)
        }
    )

#RESET FILTER ENDPOINT
@app.post("/reset_filter")
def reset_temporal_filter():
    if _temporal_filter is not None:
        _temporal_filter.reset()
        return {"status": "ok", "message": "Temporal filter reset successfully"}
    else:
       
        _temporal_filter = TemporalFilter(alpha=0.7)
        return {"status": "ok", "message": "Temporal filter created and reset successfully"}


#SET ALPHA ENDPOINT
@app.post("/set_alpha")
def set_temporal_alpha(alpha: float):

    if not 0.3 <= alpha <= 0.95:
        raise HTTPException(status_code=400, detail="Alpha must be between 0.3 and 0.95")

    temporal_filter = get_temporal_filter()
    temporal_filter.set_alpha(alpha)

    return {
        "status": "ok",
        "message": f"Alpha value set to {alpha:.2f}",
        "alpha": temporal_filter.alpha,
    }


#SHUTDOWN EVENT
@app.on_event("shutdown")
def shutdown_event():
    release_webcam()
    print("Application shut down, resources released.")



# WEBSOCKET VIDEO BAGLANTISI
@app.websocket("/ws/video_feed")
async def websocket_video_feed(websocket: WebSocket):
    
    await manager.connect(websocket)
    
   
    query_params = websocket.query_params
    try:
        process_size = int(query_params.get("process_size", 384))
    except ValueError:
        process_size = 384
        
    global _model, _device, _temporal_filter, _model_loaded
    
   
    if not _model_loaded:
        try:
            _model, _device, _ = get_cached_model(get_current_style())
            _model_loaded = True
            print(f"WebSocket: Model loaded ({get_current_style()}).")
        except Exception as e:
            print(f"WebSocket: Model could not be loaded - {e}")
            await websocket.close(code=1011, reason="Model could not be loaded")
            return
    
    #Temporal filtreyi oluşturma
    if _temporal_filter is None:
        _temporal_filter = TemporalFilter(alpha=0.7)
    else:
        _temporal_filter.reset()
        print("WebSocket: Temporal filter reset.")
    
    last_successful_frame = None
    consecutive_errors = 0
    
    print(f"WebSocket: Real time video feed started. Target Process Size: {process_size}")
    
    try:
        while True:
            try:
                frame_data = await asyncio.wait_for(websocket.receive_bytes(), timeout=90.0) #websocket üzerinden veri alma işlemi için 90 saniyelik bir zaman aşımı belirledik. Eğer bu süre içinde veri alınmazsa, asyncio.TimeoutError istisnası tetiklenecek ve döngü devam edecek. Bu, bağlantının canlı kalmasını sağlar ve uzun süre veri gelmemesi durumunda bile bağlantının kapanmasını önler.
            except WebSocketDisconnect:
                print("WebSocket: Client disconnected.")
                break
            except Exception as e:
                print(f"WebSocket: Data receive error - {e}")
                break
            
            
            try:
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    consecutive_errors += 1
                    if consecutive_errors > 5:
                        print("WebSocket: Multiple decode errors!")
                    continue
                consecutive_errors = 0
            except Exception as e:
                print(f"WebSocket: Frame decode error - {e}")
                continue
            
            
            try:
                
                def process_pipeline(img, model, device, size, filter_obj, style_id):
                    styled = apply_style_with_fallback(
                        img, model, device,
                        target_size=size,
                        use_adaptive_size=False,
                        style_id=style_id,
                    )
                    if styled is not None and filter_obj is not None:
                        return filter_obj.update(styled)
                    return styled

                filtered_frame = await asyncio.to_thread(
                    process_pipeline,
                    frame, _model, _device, process_size, _temporal_filter,
                    get_current_style(),
                )
                
                if filtered_frame is None:
                    if last_successful_frame is not None:
                        filtered_frame = last_successful_frame
                        print("WebSocket: Using fallback frame")
                    else:
                        continue
                
                last_successful_frame = filtered_frame
                
            except Exception as e:
                print(f"WebSocket: Style transfer error - {e}")
                if last_successful_frame is not None:
                    filtered_frame = last_successful_frame
                else:
                    continue
            
            # JPEG encode
            try:
                _, img_encoded = cv2.imencode('.jpg', filtered_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                result_bytes = img_encoded.tobytes()
            except Exception as e:
                print(f"WebSocket: JPEG encode error - {e}")
                continue
            
            # Gönder
            try:
                await manager.send_frame(websocket, result_bytes)
            except Exception as e:
                print(f"WebSocket: Result send error - {e}")
                break
    
    except WebSocketDisconnect:
        print("WebSocket: Connection closed.")
    except Exception as e:
        print(f"WebSocket: Unexpected error - {e}")
    finally:
        manager.disconnect(websocket)

#WEBSOCKET BILGILERI
@app.get("/ws_info")
def websocket_info():
    
    return {
        "websocket_url": "ws://localhost:8000/ws/video_feed",
        "active_connections": len(manager.active_connections),
        "model_loaded": _model_loaded,
        "temporal_filter_active": _temporal_filter is not None
    }



# VIDEO ISLEME
@app.post("/process_video")
async def process_video_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Processing video file (.mp4, .avi, .mov, .mkv)"),
    alpha: float = Form(0.7, description="Temporal filter alpha value (0.3 - 0.95)"),
    target_fps: int = Form(None, description="Target FPS (Optional; if left blank, the original FPS will be preserved.)"),
    process_size: int = Form(512, description="Process size (Example: 512 -> 512x512)"),
    return_format: str = Form("mp4", description="Output format (mp4 or avi)")
):
    
    
    
    
    if not 0.3 <= alpha <= 0.95:
        raise HTTPException(status_code=400, detail="Alpha must be between 0.3 and 0.95")
    
    if process_size < 256 or process_size > 1024:
        raise HTTPException(status_code=400, detail="Process size must be between 256-1024")
    
    if target_fps is not None and target_fps < 5:
        raise HTTPException(status_code=400, detail="Target FPS must be at least 5")
    
    
    allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    original_filename = file.filename or "video"
    file_ext = os.path.splitext(original_filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}. Supported ones: {allowed_extensions}"
        )
    
    
    session_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.mkdtemp(prefix=f"video_process_{session_id}_")
    
    input_path = os.path.join(temp_dir, f"input{file_ext}")
    output_ext = ".mp4" if return_format == "mp4" else ".avi"
    output_path = os.path.join(temp_dir, f"stylized_output{output_ext}")
    
    try:
       
        print(f"📥 Video loading: {original_filename} ({session_id})")
        
        with open(input_path, "wb") as buffer:
            
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                buffer.write(chunk)
        
        
        video_info = get_video_info(input_path)
        if 'error' in video_info:
            raise HTTPException(status_code=400, detail=f"Video dould not read: {video_info['error']}")
        
        print(f"📹 Video Informations: {video_info['width']}x{video_info['height']}, "
              f"{video_info['fps']:.2f} FPS, {video_info['frame_count']} Frame")
        
        
        model, device = get_model()
        
        # ----- 7. Temporal filtre oluştur -----
        temporal_filter = OpticalFlowFilter(alpha=alpha , flow_method='farneback')
        
        # ----- 8. İşlem boyutunu ayarla -----
        resize_dim = (process_size, process_size)
        
        # ----- 9. Video işleme fonksiyonunu çağır -----
        print(f"🎨 Video processing (alpha={alpha}, size={process_size})...")
        
        stats = process_video_file(
            input_video_path=input_path,
            output_video_path=output_path,
            style_model=model,
            device=device,
            temporal_filter=temporal_filter,
            target_fps=target_fps,
            resize_dim=resize_dim,
            verbose=False  # API'de verbose kapalı (logları karıştırmasın)
        )
        
        if stats['processed_frames'] == 0:
            raise HTTPException(status_code=500, detail="No frames could be processe!")
        
        # ----- 10. İşlenmiş videoyu döndür -----
        output_filename = f"stylized_{os.path.splitext(original_filename)[0]}{output_ext}"
        
        print(f"✅Proceessing doone: {stats['processed_frames']} frame, "
              f"{stats['elapsed_time']:.1f} seconds")
        
        return FileResponse(
            path=output_path,
            media_type="video/mp4" if return_format == "mp4" else "video/x-msvideo",
            filename=output_filename,
            background=background_tasks,
            headers={
                "X-Processing-Time": str(stats['elapsed_time']),
                "X-Processed-Frames": str(stats['processed_frames']),
                "X-Output-FPS": str(stats['output_fps'])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Video Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Error while processing video: {str(e)}")
    
    finally:
        
        def cleanup():
            try:
                print(f"🧹 Temporary files are being cleared: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Cleaning error: {e}")
        
        background_tasks.add_task(cleanup)


@app.get("/video_info")
async def get_video_info_endpoint(
    file_path: str = None,
    url: str = None
):
   
    from app.video_utils import get_video_info
    
    if file_path and os.path.exists(file_path):
        return get_video_info(file_path)
    
    return {
        "error": "No valid video file was specified",
        "usage": "GET /video_info?file_path=/path/to/video.mp4"
    }



@app.post("/video_info_upload")
async def get_uploaded_video_info(
    file: UploadFile = File(...)
):
    
    from app.video_utils import get_video_info
    import tempfile
    
    # Geçici dosyaya kaydet
    temp_dir = tempfile.mkdtemp()
    file_ext = os.path.splitext(file.filename)[1].lower()
    temp_path = os.path.join(temp_dir, f"temp{file_ext}")
    
    try:
        with open(temp_path, "wb") as buffer:
            chunk_size = 1024 * 1024
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                buffer.write(chunk)
        
        info = get_video_info(temp_path)
        info["filename"] = file.filename
        info["size_mb"] = os.path.getsize(temp_path) / (1024 * 1024)
        
        return info
        
    except Exception as e:
        return {"error": str(e)}
    
    finally:
        
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

@app.get("/styles")
async def get_styles():
    return {
        "current_style" : get_current_style(),
        "available_styles" : get_available_styles()
    }

@app.post("/set_style")
async def set_style(style_id: str):

    from app.style_transfer import reload_current_style

    global _model, _device, _temporal_filter

    
    success, error = set_current_style(style_id)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    try:
        # modeli reload et
        model, device, style_info = reload_current_style()

        # GLOBAL modeli güncelle
        _model = model
        _device = device

        # temporal filter reset
        if _temporal_filter is not None:
            _temporal_filter.reset()
            print("Temporal filter reset (for new style)")

        print(f"✅ Style changed: {style_info['name']}")

        return {
            "success": True,
            "current_style": style_id,
            "style_name": style_info['name'],
            "description": style_info['description'],
            "recommended_size": get_style_recommended_size(style_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model loading error: {str(e)}")
