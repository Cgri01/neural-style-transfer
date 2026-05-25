import React, { useState, useCallback, useEffect, useRef } from 'react';
import WebSocketCamera from './components/WebSocketCamera';
import StyledVideo from './components/StyledVideo';
import Controls from './components/Controls';
import { changeStyle, getStyles, setAlpha, healthCheck } from './api';
import { useTheme } from './context/ThemeContext';

function App() {
  const { theme, toggleTheme, isDark } = useTheme();

  const [isStreaming, setIsStreaming] = useState(true);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [latestStyledUrl, setLatestStyledUrl] = useState(null);

  const [alpha, setAlpha] = useState(0.7);
  const [targetFPS, setTargetFPS] = useState(10);
  const [processSize, setProcessSize] = useState(384);
  const [currentFPS, setCurrentFPS] = useState(0);

  const [currentStyle, setCurrentStyle] = useState('starry_night');
  const [currentStyleName, setCurrentStyleName] = useState('Starry Night');
  const [isChangingStyle, setIsChangingStyle] = useState(false);

  const alphaDebounceRef = useRef(null);

  // Backend saglik kontrolu (WebSocket'ten bagimsiz)
  useEffect(() => {
    const check = async () => {
      const ok = await healthCheck();
      setIsBackendOnline(ok);
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  // Sayfa acilirken mevcut stili al
  useEffect(() => {
    const loadCurrentStyle = async () => {
      try {
        const data = await getStyles();
        if (data.current_style) {
          setCurrentStyle(data.current_style);
        }
        const found = data.available_styles?.find((s) => s.id === data.current_style);
        if (found) setCurrentStyleName(found.name);
      } catch (error) {
        console.error('Available style could not get:', error);
      }
    };
    loadCurrentStyle();
  }, []);

  const handleStyleChange = async (styleId) => {
    if (styleId === currentStyle || isChangingStyle) return;

    setIsChangingStyle(true);
    try {
      const result = await changeStyle(styleId);
      setCurrentStyle(styleId);
      setCurrentStyleName(result.style_name || styleId);

      if (result.recommended_size && result.recommended_size !== processSize) {
        setProcessSize(result.recommended_size);
      }

      console.log(`Style changed: ${result.style_name}`);
    } catch (error) {
      console.error('Style changing error:', error);
      alert(`Style could not be changed: ${error.message}`);
    } finally {
      setIsChangingStyle(false);
    }
  };

  const handleStyledFrame = useCallback((imageUrl) => {
    setLatestStyledUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return imageUrl;
    });
  }, []);

  const handleFPSUpdate = useCallback((fps) => {
    setCurrentFPS(fps);
  }, []);

  const handleAlphaChange = (newAlpha) => {
    setAlpha(newAlpha);

    if (alphaDebounceRef.current) {
      clearTimeout(alphaDebounceRef.current);
    }
    alphaDebounceRef.current = setTimeout(() => {
      sendAlphaToBackend(newAlpha);
    }, 200);
  };

  const sendAlphaToBackend = async (value) => {
    if (!isBackendOnline) return;
    const ok = await setAlpha(value);
    if (!ok) {
      console.warn('Backend alpha update failed');
    }
  };

  // Backend acilinca mevcut alpha'yi gonder (slider sadece state tutuyordu)
  useEffect(() => {
    if (isBackendOnline) {
      sendAlphaToBackend(alpha);
    }
  }, [isBackendOnline]);

  const handleTakePhoto = useCallback(() => {
    if (!latestStyledUrl) {
      alert('No stylized images yet. Please wait a moment or start the stream...');
      return;
    }
    const link = document.createElement('a');
    const safeStyle = currentStyle.replace(/[^a-z0-9_-]/gi, '_');
    link.href = latestStyledUrl;
    link.download = `nst_${safeStyle}_${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [latestStyledUrl, currentStyle]);

  const handleFpsChange = (newFps) => {
    setTargetFPS(newFps);
  };

  const handleProcessSizeChange = (newSize) => {
    setProcessSize(newSize);
  };

  const controlsReady = isBackendOnline || isWsConnected;

  return (
    <div className="min-h-screen theme-app-bg transition-colors duration-300">
      <header className="border-b py-6" style={{ borderColor: 'var(--border-color)' }}>
        <div className="container mx-auto px-4 text-center relative">
          <button
            type="button"
            onClick={toggleTheme}
            className="absolute right-4 top-0 px-3 py-1.5 rounded-lg text-sm font-medium theme-panel theme-text-secondary hover:opacity-80 transition"
            title={isDark ? 'Light mode' : 'Dark mode'}
          >
            {isDark ? '☀️ Light' : '🌙 Dark'}
          </button>
          <h1 className="text-3xl md:text-4xl font-bold mb-2" style={{ color: 'var(--accent-gold)' }}>
            🎨 Neural Style Transfer
          </h1>
          <p className="theme-text-secondary text-sm md:text-base">
            Real Time Style Transfer
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="flex justify-center mb-6 gap-2 flex-wrap">
          <div
            className={`px-4 py-2 rounded-full text-sm font-medium ${
              isWsConnected ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-600'
            }`}
          >
            {isWsConnected ? '🟢 WebSocket Connected' : '🟡 WebSocket Connecting...'}
          </div>
          <div
            className={`px-4 py-2 rounded-full text-sm font-medium ${
              isBackendOnline ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
            }`}
          >
            {isBackendOnline ? '🟢 Backend Active' : '🔴 Backend Closed'}
          </div>
          {currentFPS > 0 && (
            <span
              className={`px-4 py-2 rounded-full text-sm ${
                currentFPS >= targetFPS * 0.8
                  ? 'bg-green-500/20 text-green-500'
                  : currentFPS >= targetFPS * 0.5
                  ? 'bg-yellow-500/20 text-yellow-600'
                  : 'bg-red-500/20 text-red-500'
              }`}
            >
              📊 {currentFPS} FPS
            </span>
          )}
        </div>

        <div className="flex flex-col lg:flex-row gap-8 justify-center items-start">
          <div className="flex-1 min-w-0">
            <div className="theme-card rounded-2xl p-4 h-full">
              <h2 className="text-lg font-semibold text-center mb-3 theme-text-secondary">
                📷 Original Webcam
              </h2>
              <WebSocketCamera
                key={`cam-${processSize}`}
                isStreaming={isStreaming}
                targetFPS={targetFPS}
                onStyledFrame={handleStyledFrame}
                onConnectionChange={setIsWsConnected}
                processSize={processSize}
                onFPSUpdate={handleFPSUpdate}
              />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="theme-card rounded-2xl p-4 h-full">
              <h2 className="text-lg font-semibold text-center mb-3 theme-text-secondary">
                🎨 Stylized
              </h2>
              <StyledVideo
                imageUrl={latestStyledUrl}
                isProcessing={false}
                fps={currentFPS}
                targetFPS={targetFPS}
                styleName={currentStyleName}
                onTakePhoto={handleTakePhoto}
                canTakePhoto={isWsConnected && !!latestStyledUrl}
              />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <Controls
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              alpha={alpha}
              onAlphaChange={handleAlphaChange}
              fps={targetFPS}
              onFpsChange={handleFpsChange}
              processSize={processSize}
              onProcessSizeChange={handleProcessSizeChange}
              currentStyle={currentStyle}
              onStyleChange={handleStyleChange}
              isChangingStyle={isChangingStyle}
              isBackendReady={controlsReady}
              isBackendOnline={isBackendOnline}
            />
          </div>
        </div>

        <div className="mt-8 max-w-2xl mx-auto text-center">
          <p className="theme-text-muted text-xs">
            FPS <span className="text-green-500">Green</span> = Fluent,{' '}
            <span className="text-yellow-500">Yellow</span> = Moderate,{' '}
            <span className="text-red-500">Red</span> = Low.
            {!isBackendOnline && ' Check if backend is working'}
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
