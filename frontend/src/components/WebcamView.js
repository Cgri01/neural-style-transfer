import React, { useRef, useEffect, useState, useCallback } from 'react';

const WebcamView = ({ onFrameCapture , isStreaming = true , targetFPS = 10}) => {

  //DOM Referansları:
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  //Animasyon ve throttle için referanslar:
  const animationIdRef = useRef(null);
  const lastCaptureTimeRef = useRef(0);
  const frameRequestIdRef = useRef(0);

  //Stateler:
  const [isWebcamReady , setIsWebcamReady] = useState(false);
  const [error , setError] = useState(null);
  const [currentFPS , setCurrentFPS] = useState(0);

  //FPS Hesaplama:
  const frameTimesRef = useRef([]);
  const fpsIntervalRef = useRef(null);

  //Hedef frame aralığı (ms cinsinden):
  const targetInterval = 1000 / targetFPS // örnek olarak 10 fps = 100ms

  
  //FONKSIYONLAR

  // WEBCAM BASLATMA:
  const initWebcam = useCallback(async () => {
    try {
      setError(null);
      setIsWebcamReady(false);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: {ideal:640},
          height: {ideal:480},
          facingMode: "user"
        },
        audio: false
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;

        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play();
          setIsWebcamReady(true);
          console.log(`Webcam initialized successfully! Target FPS is ${targetFPS}`);

        };
      }



    } catch (error) {
      console.error("Webcam Error:" , error);
      setError(`Webcem access is failed: ${error.message}`)
      setIsWebcamReady(false);
    }
  } , [targetFPS]);


  //WEBCAM DURDURMA
  const stopWebcam = useCallback( () => {
    
    //Animation frame durdur:
    if (animationIdRef.current) {
      cancelAnimationFrame(animationIdRef.current);
      animationIdRef.current = null;
    }

    //FPS Hesaplama Intervalini durdurma:
    if (fpsIntervalRef.current) {
      clearInterval(fpsIntervalRef.current);
      fpsIntervalRef.current = null;
    }

    //Streami durdurma:
    if (streamRef.current){
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    //Video Elementlerini temizleme:
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    //Frame Sayaçlarını sıfırlama:
    lastCaptureTimeRef.current = 0;
    frameTimesRef.current = [];
    setCurrentFPS(0);
    setIsWebcamReady(false);

    console.log("Webcam has been stopped")
  } , []);


  //KARE YAKALAMA:
  const captureFrame = useCallback( async () => {

    if (!videoRef.current || !canvasRef.current) { return false;}

    const video = videoRef.current;
    const canvas = canvasRef.current;

    //Video hazır değilse atla:
    if (video.readyState !== 4) { return false;}

    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    
    //Kareyi canvasa çizme:
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video , 0 , 0, canvas.width , canvas.height );

    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        if (blob && onFrameCapture) {
          onFrameCapture(blob);

        }
        resolve( blob !== null);
      }, "image/jpeg" , 0.85);
    });

  } , [onFrameCapture]);

  //FPS HESAPLAMA ve THROTTLE KONTROLU:

  //FPS HESAPLAMA:
  const updateFPS = useCallback(() => {
    const now = performance.now();
    frameTimesRef.current.push(now);

    //Son 1 saniyedeki frameleri tutacagız:
    const oneSecondAgo = now - 1000;
    frameTimesRef.current = frameTimesRef.current.filter(time => time > oneSecondAgo);

    const fps = frameTimesRef.current.length;
    setCurrentFPS(fps);
  } , [])

  //ANA CAPTURE DONGUSU
  const throttledCaptureLoop = useCallback((currentTime) => {
    if (!isStreaming || !isWebcamReady) {
      animationIdRef.current = requestAnimationFrame(throttledCaptureLoop);
      return;
    }

    //throttle kontrolu: Son capturedan bu yana gecen süre
    const timeSinceLastCapture = currentTime - lastCaptureTimeRef.current;

    if (timeSinceLastCapture >= targetInterval) {
      //Capture
      lastCaptureTimeRef.current = currentTime;

      captureFrame().then(success => {
        if (success) {
          updateFPS();
        }
      }).catch(error => {
        console.warn("Frame Capture error" , error);
      });

    }

      //Bir sonraki frame için devam:
      animationIdRef.current = requestAnimationFrame(throttledCaptureLoop);

    

  } , [isStreaming, isWebcamReady, targetInterval, captureFrame, updateFPS]);

  //FPS GOSTERGESI INTERVALI
  const startFPSMonitor = useCallback(() => {
    if (fpsIntervalRef.current){
      clearInterval(fpsIntervalRef.current);
    }

    fpsIntervalRef.current = setInterval(() => {
      if (!isStreaming || !isWebcamReady) {
        setCurrentFPS(0);
      }
    } , 1000);

  } , [isStreaming , isWebcamReady]);



  //USEEFFECT ILE YASAM DONGUSU:

  //WEBCAM BASLAT(bileşen yüklendiğinde)
  useEffect(() => {
    initWebcam();

    return () => {
      stopWebcam();
    };
  } , [initWebcam , stopWebcam]);

  //CAPTURE DONGUSU
  useEffect(() => {
    if (isStreaming && isWebcamReady) {
      console.log(`Frame capturing started (Throttle: ${targetInterval} )`);
      lastCaptureTimeRef.current = performance.now();
      animationIdRef.current = requestAnimationFrame(throttledCaptureLoop);
      startFPSMonitor();
    } else {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
        animationIdRef.current = null;
      }
      console.log("Frame capturing is being stopped")

    }

    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
        animationIdRef.current = null;
      }
      if (fpsIntervalRef.current) {
        clearInterval(fpsIntervalRef.current);
        fpsIntervalRef.current = null;
      }
    };
  } , [isStreaming, isWebcamReady, throttledCaptureLoop, startFPSMonitor, targetInterval])


  //RENDER KISMI:
  return (
    <div className="relative w-full max-w-3xl mx-auto">
      <div className="relative rounded-xl overflow-hidden bg-dark-bg shadow-xl">
        
        {/* Video elementi */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`w-full h-auto block -scale-x-100 transition-opacity duration-300 ${
            isWebcamReady ? 'opacity-100' : 'opacity-50'
          }`}
        />
        
        {/* Canvas (gizli - sadece kare yakalamak için) */}
        <canvas ref={canvasRef} className="hidden" />
        
        {/* FPS Göstergesi (sadece aktifken) */}
        {isStreaming && isWebcamReady && currentFPS > 0 && (
          <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1">
            <span className={`text-xs font-mono ${
              currentFPS >= targetFPS * 0.8 ? 'text-green-400' : 'text-yellow-400'
            }`}>
              🎬 {currentFPS} FPS
            </span>
          </div>
        )}
        
        {/* Hedef FPS göstergesi (tooltip) */}
        <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1">
          <span className="text-xs text-gray-300">
            🎯 {targetFPS} FPS
          </span>
        </div>
        
        {/* Yükleme göstergesi */}
        {!isWebcamReady && !error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 text-white">
            <div className="w-12 h-12 border-4 border-white/30 border-t-accent-blue rounded-full animate-spin"></div>
            <p className="mt-4 text-sm">Webcam initializing...</p>
          </div>
        )}
        
        {/* Hata mesajı */}
        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 text-center p-5">
            <p className="text-red-400 mb-3">⚠️ {error}</p>
            <button 
              onClick={initWebcam}
              className="bg-accent-blue hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition"
            >
              Try again!
            </button>
          </div>
        )}
      </div>
      
      {/* Bilgi çubuğu */}
      <div className="flex justify-center gap-4 mt-4">
        <span className={`px-3 py-1 rounded-full text-white text-xs font-medium ${
          isWebcamReady ? 'bg-green-500' : 'bg-gray-500'
        }`}>
          {isWebcamReady ? '📹 Webcam Active' : '⏳ Waiting...'}
        </span>
        
        {isWebcamReady && (
          <span className={`px-3 py-1 rounded-full text-white text-xs font-medium ${
            isStreaming ? 'bg-accent-blue animate-pulse-slow' : 'bg-gray-500'
          }`}>
            {isStreaming ? '🎬 Frame Capturing...' : '⏸️ Stopped'}
          </span>
        )}
      </div>
      
      {/* Performans notu */}
      {isStreaming && isWebcamReady && currentFPS < targetFPS * 0.5 && (
        <div className="mt-3 text-center">
          <p className="text-yellow-400 text-xs">
            ⚠️Low FPS: Target FPS is unattainable due to backend processing load.
          </p>
        </div>
      )}
    </div>
  );
};


export default WebcamView;