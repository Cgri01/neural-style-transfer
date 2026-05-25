import React , {useRef, useState , useEffect , useCallback, useMemo} from "react";
import useWebSocket from "../hooks/useWebSocket";
import { getWebSocketURL } from "../api";



const WebSocketCamera = ({ 
  isStreaming = true, 
  targetFPS = 10,
  onStyledFrame,
  onConnectionChange,
  processSize = 384,
  onFPSUpdate
}) => {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const streamRef = useRef(null);
    const animationIdRef = useRef(null);
    const lastCaptureTimeRef = useRef(0);

    const [isWebcamReady , setIsWebcamReady] = useState(false);
    const [error , setError] = useState(null);
    const [currentFPS , setCurrentFPS] = useState(0);
    const frameTimesRef = useRef([]);

    //FPS Hesaplama için frame sayacı:
    const frameCountRef = useRef(0);
    const lastFPSTimeRef = useRef(performance.now());


    //Websocket bağlantısı (REACT_APP_API_URL üzerinden):
    const wsUrl = useMemo(() => getWebSocketURL(processSize), [processSize]);
    const { isConnected, connect, disconnect, send } = useWebSocket(
    wsUrl,
    (styledBlob) => {
        // Stilize geldiğinde:
        if (onStyledFrame) {
            const url = URL.createObjectURL(styledBlob);
            onStyledFrame(url);

            //Her gelen Frame'de FPS hesapla:
            frameCountRef.current ++;
            const now = performance.now();
            const elapsed = now - lastFPSTimeRef.current;

            if (elapsed >= 1000) {
              const fps = Math.round(frameCountRef.current * 1000 / elapsed);
              setCurrentFPS(fps);
              if (onFPSUpdate) onFPSUpdate(fps);
              frameCountRef.current = 0;
              lastFPSTimeRef.current = now;
            }

        }
    },
    // ON OPEN: Bağlantı açıldığında
    () => {
        console.log("Websocket connected , video stream can start");
        setError(null); // ✨ Bağlantı sağlandığı an hatayı siliyoruz
        frameCountRef.current = 0; //baglantı kuruldugunda fps sayaclarını sıfırlıyoruz
        lastCaptureTimeRef.current = performance.now(); 
        if (onConnectionChange) onConnectionChange(true);
    },
    // ON CLOSE: Bağlantı kapandığında
    () => {
        console.log("Websocket connection closed!");
        if (onConnectionChange) onConnectionChange(false);
        setCurrentFPS(0);
        if (onFPSUpdate) onFPSUpdate(0);
    },
    // ON ERROR: Hata oluştuğunda
    (err) => {
        // EĞER ZATEN BAĞLIYSAK, GEÇİCİ HATALARI EKRANA BASMA
        if (!isConnected) {
            console.error("Websocket error: ", err);
            setError("Websocket connection error!");
        }
        if (onConnectionChange) onConnectionChange(false);
        setCurrentFPS(0);
        if (onFPSUpdate) onFPSUpdate(0);
    }
);


    //Websocketi bagla:
    useEffect(() => {
        connect();
        return () => disconnect();

    } , [connect , disconnect]);

    //Webcami baslatma:
    const initWebcam = useCallback(async () => {
        try {
            setError(null);
            setIsWebcamReady(false);

            const stream = await navigator.mediaDevices.getUserMedia({
                video : {width : {ideal: 640} , height: {ideal:480} , facingMode: "user"},
                audio:false
            });

            streamRef.current = stream;

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.onloadedmetadata = () => {
                    videoRef.current.play();
                    setIsWebcamReady(true);
                    console.log("Webcam successfully initialized!");
                };
            }

        } catch (error) {
            console.error("Webcam error" , error);
            setError(`Webcam access unsuccessfull: ${error.message}`);
            setIsWebcamReady(false);
            
        }
    }, [])

    //Webcam durdurma:
    const stopWebcam = useCallback(() => {
        if (animationIdRef.current) {
            cancelAnimationFrame(animationIdRef.current);
            animationIdRef.current = null;
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }

        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }

        setIsWebcamReady(false);
    } , []);

    //FPS Hesaplama:
    const updateFPS = useCallback(() => {
        const now = performance.now();
        frameTimesRef.current.push(now);
        const onSecondAgo = now - 1000;
        frameTimesRef.current = frameTimesRef.current.filter(time => time > onSecondAgo);
        setCurrentFPS(frameTimesRef.current.length);
    }, []);


    //FRAME YAKALAMA VE GONDERME:
    const captureAndSend = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !isConnected || !isStreaming) {
      return false;
    }
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    if (video.readyState !== 4) return false;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Canvas'ı JPEG Blob'a çevir
    canvas.toBlob((blob) => {
      if (blob && isConnected && isStreaming) {
        blob.arrayBuffer().then(buffer => {
          send(buffer);
          updateFPS();
        });
      }
    }, 'image/jpeg', 0.85);
    
    return true;
  }, [isConnected, isStreaming, send, updateFPS]);

  //Throtle ile capture dongusu:
  // Throttle ile capture döngüsü
  const targetInterval = 1000 / targetFPS;
  
  const captureLoop = useCallback((currentTime) => {
    if (!isStreaming || !isWebcamReady || !isConnected) {
      animationIdRef.current = requestAnimationFrame(captureLoop);
      return;
    }
    
    const timeSinceLastCapture = currentTime - lastCaptureTimeRef.current;
    
    if (timeSinceLastCapture >= targetInterval) {
      lastCaptureTimeRef.current = currentTime;
      captureAndSend();
    }
    
    animationIdRef.current = requestAnimationFrame(captureLoop);
  }, [isStreaming, isWebcamReady, isConnected, targetInterval, captureAndSend]);

  // Başlangıç ve temizlik
  useEffect(() => {
    initWebcam();
    return () => stopWebcam();
  }, [initWebcam, stopWebcam]);

  // Capture döngüsünü başlat/durdur
  useEffect(() => {
    if (isStreaming && isWebcamReady && isConnected) {
      lastCaptureTimeRef.current = performance.now();
      animationIdRef.current = requestAnimationFrame(captureLoop);
    } else if (animationIdRef.current) {
      cancelAnimationFrame(animationIdRef.current);
      animationIdRef.current = null;
    }
  }, [isStreaming, isWebcamReady, isConnected, captureLoop]);

  // WebSocket bağlantı durumu değiştiğinde
  useEffect(() => {
    if (onConnectionChange) {
      onConnectionChange(isConnected);
    }
  }, [isConnected, onConnectionChange]);

  return (
    <div className="relative w-full max-w-3xl mx-auto">
      <div className="relative rounded-xl overflow-hidden shadow-xl" style={{ backgroundColor: 'var(--bg-primary)' }}>
        
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`w-full h-auto block -scale-x-100 transition-opacity duration-300 ${
            isWebcamReady ? 'opacity-100' : 'opacity-50'
          }`}
        />
        
        <canvas ref={canvasRef} className="hidden" />

        {/* FPS GOSTERGESI */}
        {isStreaming && isWebcamReady && isConnected && currentFPS > 0 && (
          <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1">
            <div className="flex items-center gap-1">
              <span className={`text-xs font-mono font-bold ${
                currentFPS >= targetFPS *0.8 ? "text-green-400" :
                currentFPS >= targetFPS * 0.5 ? "text-yellow-400" : "text-red-400"
                }`}>
                  {currentFPS} / {targetFPS} FPS
                </span>

            </div>
          </div>
        )}


        
        {/* WebSocket bağlantı hatası */}
        {/* {!isConnected && isStreaming && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 text-white">
            <div className="w-12 h-12 border-4 border-white/30 border-t-red-500 rounded-full animate-spin"></div>
            <p className="mt-4 text-sm">WebSocket Connecting...</p>
            <p className="text-xs text-gray-400 mt-2">is Backend working?</p>
          </div>
        )} */}
        
        {/* Webcam yükleniyor */}
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
              Try Again
            </button>
          </div>
        )}
      </div>
      
      <div className="flex justify-center gap-4 mt-4">
        <span className={`px-3 py-1 rounded-full text-white text-xs font-medium ${
          isWebcamReady ? 'bg-green-500' : 'bg-gray-500'
        }`}>
          {isWebcamReady ? '📹 Webcam Active' : '⏳ Waiting...'}
        </span>
        <span className={`px-3 py-1 rounded-full text-white text-xs font-medium ${
          isConnected ? 'bg-accent-blue' : 'bg-gray-500'
        }`}>
          {isConnected ? '🔌 WebSocket Connected' : '🔌 WebSocket Not Connected'}
        </span>
      </div>
    </div>
  );
};

export default WebSocketCamera;



