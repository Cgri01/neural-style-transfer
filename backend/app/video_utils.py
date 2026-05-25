import cv2
import numpy as np
import time
import os
import time
from tqdm import tqdm

# Global değişken: webcam nesnesini (cap) fonksiyonlar arasında paylaşmak için
_cap = None
_last_frame_time = 0

def get_webcam_frame(camera_id=0, retry_count=3):

    global _cap, _last_frame_time
    
    # Eğer daha önce açılmamışsa webcam'i aç
    if _cap is None:
        _cap = cv2.VideoCapture(camera_id)
        if not _cap.isOpened():
            print(f"Webcam (ID={camera_id}) could not be opened!")
            return None
        
        # Kamera ayarlarını optimize et (daha hızlı okuma için)
        _cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Tampon boyutunu azalt
        _cap.set(cv2.CAP_PROP_FPS, 30)        # FPS ayarla
        
        # Kameranın ısınması için biraz bekle
        time.sleep(0.2)
    
    # Birden fazla deneme hakkı tanı
    for attempt in range(retry_count):
        # Kameradan kare oku
        ret, frame = _cap.read()
        
        if ret and frame is not None:
            _last_frame_time = time.time()
            return frame
        
        # Başarısız olursa kısa bekle ve tekrar dene
        if attempt < retry_count - 1:
            print(f"Frame could not be read, retrying... ({attempt+1}/{retry_count})")
            time.sleep(0.05)
    
    print("ERROR: Could not capture frame after multiple attempts!")
    return None

def release_webcam():
  
    global _cap
    if _cap is not None:
        _cap.release()
        _cap = None
        print("Webcam released.")

def reset_webcam():
   
    global _cap
    release_webcam()
    print("Webcam resetted, will reconnect.")



def process_video_file(
    input_video_path,
    output_video_path,
    style_model,
    device,
    temporal_filter=None,
    target_fps=None,
    resize_dim=None,
    verbose=True
):
    
   
    from app.style_transfer import apply_style
    
    # ----- 1. Girdi kontrolü -----
    if not os.path.exists(input_video_path):
        raise FileNotFoundError(f"Video file not found!: {input_video_path}")
    
    # ----- 2. Video dosyasını aç -----
    cap = cv2.VideoCapture(input_video_path)
    
    if not cap.isOpened():
        raise RuntimeError(f"Video File could not opened: {input_video_path}")
    
    # Video özelliklerini al
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Çıktı FPS'ini belirle
    output_fps = target_fps if target_fps else original_fps
    
    # İşlem boyutunu belirle
    if resize_dim:
        process_width, process_height = resize_dim
    else:
        process_width, process_height = original_width, original_height
    
    if verbose:
        print("=" * 60)
        print("Video Style Transfer Starting")
        print("=" * 60)
        print(f"Input File: {input_video_path}")
        print(f"Output File: {output_video_path}")
        print(f"Original size: {original_width}x{original_height}")
        print(f"Processed file: {process_width}x{process_height}")
        print(f"Original FPS: {original_fps:.2f}")
        print(f"Output FPS: {output_fps:.2f}")
        print(f"Total frame: {total_frames}")
        print("=" * 60)
    
    # ----- 3. Video yazıcıyı hazırla -----
    # Çıktı klasörünü oluştur (yoksa)
    output_dir = os.path.dirname(output_video_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # FourCC kodu (MP4 için 'mp4v' veya 'avc1')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    # VideoWriter nesnesi (orijinal boyutlarda yazacağız)
    out = cv2.VideoWriter(output_video_path, fourcc, output_fps, (original_width, original_height))
    
    if not out.isOpened():
        cap.release()
        raise RuntimeError(f"Video writer could not be created: {output_video_path}")
    
    # ----- 4. Frame işleme döngüsü -----
    frame_count = 0
    processed_count = 0
    start_time = time.time()
    
    # İlerleme çubuğu
    if verbose:
        pbar = tqdm(total=total_frames, desc="processing", unit="frame")
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            frame_count += 1
            
            # ----- 4.1. Frame'i işleme boyutuna ölçeklendir -----
            if resize_dim and (process_width, process_height) != (original_width, original_height):
                process_frame = cv2.resize(frame, (process_width, process_height))
            else:
                process_frame = frame.copy()
            
            # ----- 4.2. Stil transferi uygula -----
            try:
                styled_frame = apply_style(process_frame, style_model, device)
                
                if styled_frame is None:
                    if verbose:
                        print(f"\nWarning:  {frame_count} Frame not processed, using original.")
                    styled_frame = process_frame
                
            except Exception as e:
                if verbose:
                    print(f"\nError: Error while processing {frame_count} frame: {e}")
                styled_frame = process_frame
            
            # ----- 4.3. Temporal filtre uygula -----
            if temporal_filter is not None:
                styled_frame = temporal_filter.update(styled_frame)
            
            # ----- 4.4. Orijinal boyuta geri ölçeklendir -----
            if (styled_frame.shape[1], styled_frame.shape[0]) != (original_width, original_height):
                styled_frame = cv2.resize(styled_frame, (original_width, original_height))
            
            # ----- 4.5. Video dosyasına yaz -----
            out.write(styled_frame)
            processed_count += 1
            
            # ----- 4.6. İlerleme çubuğunu güncelle -----
            if verbose:
                pbar.update(1)
                
                # Her 100 karede bir tahmini süreyi göster
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    fps_processing = frame_count / elapsed
                    remaining_frames = total_frames - frame_count
                    eta = remaining_frames / fps_processing if fps_processing > 0 else 0
                    pbar.set_postfix({
                        'FPS': f'{fps_processing:.1f}',
                        'ETA': f'{eta:.0f}s'
                    })
    
    except KeyboardInterrupt:
        if verbose:
            print("\n\n⚠️ Processing stopped by the user!")
    
    finally:
        # ----- 5. Kaynakları temizle -----
        cap.release()
        out.release()
        
        if verbose:
            pbar.close()
        
        elapsed_time = time.time() - start_time
        
        # ----- 6. İstatistikleri hesapla -----
        fps_processing = processed_count / elapsed_time if elapsed_time > 0 else 0
        
        stats = {
            'total_frames': total_frames,
            'processed_frames': processed_count,
            'skipped_frames': frame_count - processed_count,
            'elapsed_time': elapsed_time,
            'fps_processed': fps_processing,
            'input_fps': original_fps,
            'output_fps': output_fps,
            'input_size': (original_width, original_height),
            'process_size': (process_width, process_height),
            'output_path': output_video_path
        }
        
        if verbose:
            print("\n" + "=" * 60)
            print("Transaction Completed!")
            print("=" * 60)
            print(f"Processed frame: {processed_count}/{total_frames}")
            print(f"Executed time: {elapsed_time:.2f} saniye")
            print(f"Processing speed: {fps_processing:.2f} FPS")
            print(f"Output file: {output_video_path}")
            print("=" * 60)
        
    return stats


#VİDEO BILGISI
def get_video_info(video_path):
    
    if not os.path.exists(video_path):
        return {'error': 'File could not find'}
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return {'error': 'Video could not oppened'}
    
    info = {
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0
    }
    
    cap.release()
    return info