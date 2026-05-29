import React, { useState, useRef, useCallback } from 'react';
import { sendFrameToBackend, getStyles, changeStyle } from '../api';


const SIZES = [512, 640, 1024];

const PhotoProcessor = ({ isBackendOnline }) => {
  const [sourceImage, setSourceImage] = useState(null);
  const [sourceBlob, setSourceBlob] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [processSize, setProcessSize] = useState(512);
  const [currentStyle, setCurrentStyle] = useState('starry_night');
  const [availableStyles, setAvailableStyles] = useState([]);
  const [processingTime, setProcessingTime] = useState(null);

  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // Stilleri yükle
  React.useEffect(() => {
    getStyles().then((data) => {
      setAvailableStyles(data.available_styles || []);
      if (data.current_style) setCurrentStyle(data.current_style);
    });
  }, []);

  // Dosya yükleme
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setError(null);
    setResultUrl(null);
    setProcessingTime(null);
    setSourceBlob(file);
    const reader = new FileReader();
    reader.onload = (ev) => setSourceImage(ev.target.result);
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    setError(null);
    setResultUrl(null);
    setProcessingTime(null);
    setSourceBlob(file);
    const reader = new FileReader();
    reader.onload = (ev) => setSourceImage(ev.target.result);
    reader.readAsDataURL(file);
  };

  // Kamera
  const openCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      setIsCameraOpen(true);
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
      }, 100);
    } catch (err) {
      setError('Kamera açılamadı: ' + err.message);
    }
  }, []);

  const closeCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setIsCameraOpen(false);
  }, []);

const captureFromCamera = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    
    // Aynalama ekle
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    
    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      setSourceBlob(blob);
      setSourceImage(canvas.toDataURL('image/jpeg'));
      setResultUrl(null);
      setProcessingTime(null);
      setError(null);
      closeCamera();
    }, 'image/jpeg', 0.95);
  }, [closeCamera]);
  // İşle
  const handleProcess = async () => {
    if (!sourceBlob) return;
    setIsProcessing(true);
    setError(null);
    setResultUrl(null);
    setProgress(0);

    //Seçilen stili backende bildirme:
    try {
        await changeStyle(currentStyle);
    } catch (err) {
        setError('Style could not changed: ' + err.message);
        setIsProcessing(false);
        return;
    }

    //Progress:
    const progressInterval = setInterval(() => {
        setProgress((p) => {
            if (p >= 85 ) {clearInterval(progressInterval); return p;}
            return p + Math.random() * 12;
        });
    } , 400);

    const startTime = Date.now();
    try {
        const result = await sendFrameToBackend(sourceBlob, processSize);
        if (!result) throw new Error('No result from backend');
        clearInterval(progressInterval);
        setProgress(100);
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        setProcessingTime(elapsed);
        const url = URL.createObjectURL(result);
        setResultUrl(url);
    } catch (err) {
        clearInterval(progressInterval);
        setError('Processing failed: ' + err.message);
    } finally {
        setIsProcessing(false);
    }

  };

  const handleDownload = () => {
    if (!resultUrl) return;
    const a = document.createElement('a');
    a.href = resultUrl;
    a.download = `nst_${currentStyle}_${processSize}px_${Date.now()}.jpg`;
    a.click();
  };

  const handleReset = () => {
    setSourceImage(null);
    setSourceBlob(null);
    setResultUrl(null);
    setError(null);
    setProgress(0);
    setProcessingTime(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    closeCamera();
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">

      {/* Ayarlar */}
      <div className="theme-card rounded-2xl p-5 mb-6 flex flex-wrap gap-6 items-end">
        {/* Stil seçimi */}
        <div className="flex-1 min-w-[180px]">
          <label className="block text-xs theme-text-muted mb-1">🎨 Stil</label>
          <select
            value={currentStyle}
            onChange={(e) => setCurrentStyle(e.target.value)}
            disabled={isProcessing}
            className="w-full px-3 py-2 theme-input border rounded-lg text-sm focus:outline-none disabled:opacity-50"
          >
            {availableStyles.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        {/* Çözünürlük */}
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs theme-text-muted mb-1">📐 Resolution</label>
          <select
            value={processSize}
            onChange={(e) => setProcessSize(Number(e.target.value))}
            disabled={isProcessing}
            className="w-full px-3 py-2 theme-input border rounded-lg text-sm focus:outline-none disabled:opacity-50"
          >
            {SIZES.map((s) => (
              <option key={s} value={s}>{s}×{s}px {s === 1024 ? '(Higher Resolution)' : s === 640 ? '(Balanced)' : '(Fast)'}</option>
            ))}
          </select>
        </div>

        {/* Backend durumu */}
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full ${isBackendOnline ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="theme-text-muted">{isBackendOnline ? 'Backend active' : 'Backend offline'}</span>
        </div>
      </div>

      {/* Kaynak seçimi */}
      {!sourceImage && !isCameraOpen && (
        <div className="theme-card rounded-2xl p-6 mb-6">
          <div className="grid grid-cols-2 gap-4 mb-6">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="py-10 rounded-xl border-2 border-dashed flex flex-col items-center gap-3 transition hover:opacity-70"
              style={{ borderColor: 'var(--border-color)' }}
            >
              <span className="text-4xl">📁</span>
              <span className="text-sm theme-text-secondary font-medium">Upload from File</span>
              <span className="text-xs theme-text-muted">JPG, PNG, WEBP</span>
            </button>
            <button
              type="button"
              onClick={openCamera}
              className="py-10 rounded-xl border-2 border-dashed flex flex-col items-center gap-3 transition hover:opacity-70"
              style={{ borderColor: 'var(--border-color)' }}
            >
              <span className="text-4xl">📷</span>
              <span className="text-sm theme-text-secondary font-medium">Capture from Webcam</span>
              <span className="text-xs theme-text-muted">Instant Photo</span>
            </button>
          </div>
          <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />

          {/* Drag & drop */}
          <div
            className="rounded-xl p-6 text-center border border-dashed transition hover:opacity-70 cursor-pointer"
            style={{ borderColor: 'var(--border-color)' }}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
          >
            <p className="text-sm theme-text-muted">or drag and drop a photo here</p>
          </div>
        </div>
      )}

      {/* Kamera */}
      {isCameraOpen && (
        <div className="theme-card rounded-2xl overflow-hidden mb-6">
          <div className="relative">
            <video ref={videoRef} autoPlay playsInline muted className="w-full h-auto block -scale-x-100" />
            <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-3">
              <button
                type="button"
                onClick={captureFromCamera}
                className="px-6 py-2.5 rounded-full text-white font-medium shadow-lg transition hover:scale-105"
                style={{ backgroundColor: 'var(--accent-blue)' }}
              >
                📸 Capture
              </button>
              <button
                type="button"
                onClick={closeCamera}
                className="px-6 py-2.5 rounded-full text-white font-medium shadow-lg bg-gray-600 hover:bg-gray-500 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Önizleme + Sonuç */}
      {sourceImage && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {/* Orijinal */}
            <div className="theme-card rounded-2xl overflow-hidden">
              <div className="px-4 py-2 border-b text-xs theme-text-muted" style={{ borderColor: 'var(--border-color)' }}>
                📷 Original
              </div>
              <img src={sourceImage} alt="Original" className="w-full h-auto block" />
            </div>

            {/* Sonuç */}
            <div className="theme-card rounded-2xl overflow-hidden">
              <div className="px-4 py-2 border-b text-xs theme-text-muted flex justify-between" style={{ borderColor: 'var(--border-color)' }}>
                <span>🎨 Stylized {currentStyle && `— ${currentStyle}`}</span>
                {processingTime && <span className="text-green-400">✓ {processingTime}s</span>}
              </div>
              <div className="min-h-[200px] flex items-center justify-center" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                {isProcessing ? (
                  <div className="w-full p-6">
                    <p className="text-xs theme-text-muted text-center mb-3">Processing... {Math.round(progress)}%</p>
                    <div className="w-full h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border-color)' }}>
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{ width: `${progress}%`, backgroundColor: 'var(--accent-blue)' }}
                      />
                    </div>
                  </div>
                ) : resultUrl ? (
                  <img src={resultUrl} alt="Stylized" className="w-full h-auto block" />
                ) : (
                  <p className="text-xs theme-text-muted p-8 text-center">
                    Stylize button
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Hata */}
          {error && (
            <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              ⚠️ {error}
            </div>
          )}

          {/* Butonlar */}
          <div className="flex gap-3 flex-wrap">
            <button
              type="button"
              onClick={handleProcess}
              disabled={isProcessing || !isBackendOnline}
              className="px-7 py-3 rounded-xl text-white font-medium transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
              style={{ backgroundColor: 'var(--accent-blue)' }}
            >
              {isProcessing ? '⏳ Processing...' : '✨ Stylize'}
            </button>

            {resultUrl && (
              <button
                type="button"
                onClick={handleDownload}
                className="px-7 py-3 rounded-xl text-white font-medium transition-all hover:scale-[1.02] shadow-md bg-green-600 hover:bg-green-500"
              >
                ⬇️ Download
              </button>
            )}

            <button
              type="button"
              onClick={handleReset}
              disabled={isProcessing}
              className="px-7 py-3 rounded-xl font-medium transition-all hover:opacity-80 theme-panel theme-text-secondary disabled:opacity-50"
            >
              🔄 Reset
            </button>
          </div>
        </>
      )}

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
};

export default PhotoProcessor;