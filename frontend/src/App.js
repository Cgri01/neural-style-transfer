import React, { useState, useCallback, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import WebSocketCamera from './components/WebSocketCamera';
import StyledVideo from './components/StyledVideo';
import Controls from './components/Controls';
import PhotoProcessor from './components/PhotoProcessor';
import { changeStyle, getStyles, setAlpha, healthCheck } from './api';
import { useTheme } from './context/ThemeContext';

// ── Sayfa: Live ───────────────────────────────────────────────
function LivePage({
  isStreaming, setIsStreaming,
  isWsConnected, setIsWsConnected,
  isBackendOnline,
  latestStyledUrl, setLatestStyledUrl,
  alpha, targetFPS, setTargetFPS,
  processSize, setProcessSize,
  currentFPS, setCurrentFPS,
  currentStyle, setCurrentStyle,
  currentStyleName, setCurrentStyleName,
  isChangingStyle, setIsChangingStyle,
  alphaDebounceRef,
}) {
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
    } catch (error) {
      alert(`Stil değiştirilemedi: ${error.message}`);
    } finally {
      setIsChangingStyle(false);
    }
  };

  const handleStyledFrame = useCallback((imageUrl) => {
    setLatestStyledUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return imageUrl; });
  }, [setLatestStyledUrl]);

  const handleTakePhoto = useCallback(() => {
    if (!latestStyledUrl) { alert('Henüz stilize görüntü yok.'); return; }
    const link = document.createElement('a');
    link.href = latestStyledUrl;
    link.download = `nst_${currentStyle}_${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [latestStyledUrl, currentStyle]);

  const handleAlphaChange = (newAlpha) => {
    if (alphaDebounceRef.current) clearTimeout(alphaDebounceRef.current);
    alphaDebounceRef.current = setTimeout(async () => {
      if (isBackendOnline) await setAlpha(newAlpha);
    }, 200);
  };

  const controlsReady = isBackendOnline || isWsConnected;

  return (
    <div className="flex flex-col lg:flex-row gap-8 justify-center items-start">
      <div className="flex-1 min-w-0">
        <div className="theme-card rounded-2xl p-4 h-full">
          <h2 className="text-lg font-semibold text-center mb-3 theme-text-secondary">📷 Original Webcam</h2>
          <WebSocketCamera
            key={`cam-${processSize}`}
            isStreaming={isStreaming}
            targetFPS={targetFPS}
            onStyledFrame={handleStyledFrame}
            onConnectionChange={setIsWsConnected}
            processSize={processSize}
            onFPSUpdate={setCurrentFPS}
          />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="theme-card rounded-2xl p-4 h-full">
          <h2 className="text-lg font-semibold text-center mb-3 theme-text-secondary">🎨 Stylized</h2>
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
          onFpsChange={setTargetFPS}
          processSize={processSize}
          onProcessSizeChange={setProcessSize}
          currentStyle={currentStyle}
          onStyleChange={handleStyleChange}
          isChangingStyle={isChangingStyle}
          isBackendReady={controlsReady}
          isBackendOnline={isBackendOnline}
        />
      </div>
    </div>
  );
}

// ── Ana App ───────────────────────────────────────────────────
function App() {
  const { toggleTheme, isDark } = useTheme();

  const [isStreaming, setIsStreaming] = useState(true);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [latestStyledUrl, setLatestStyledUrl] = useState(null);

  const [alpha, setAlphaState] = useState(0.7);
  const [targetFPS, setTargetFPS] = useState(10);
  const [processSize, setProcessSize] = useState(384);
  const [currentFPS, setCurrentFPS] = useState(0);

  const [currentStyle, setCurrentStyle] = useState('starry_night');
  const [currentStyleName, setCurrentStyleName] = useState('Starry Night');
  const [isChangingStyle, setIsChangingStyle] = useState(false);

  const alphaDebounceRef = useRef(null);

  useEffect(() => {
    const check = async () => { const ok = await healthCheck(); setIsBackendOnline(ok); };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    getStyles().then((data) => {
      if (data.current_style) setCurrentStyle(data.current_style);
      const found = data.available_styles?.find((s) => s.id === data.current_style);
      if (found) setCurrentStyleName(found.name);
    });
  }, []);

  const sharedProps = {
    isStreaming, setIsStreaming,
    isWsConnected, setIsWsConnected,
    isBackendOnline,
    latestStyledUrl, setLatestStyledUrl,
    alpha, targetFPS, setTargetFPS,
    processSize, setProcessSize,
    currentFPS, setCurrentFPS,
    currentStyle, setCurrentStyle,
    currentStyleName, setCurrentStyleName,
    isChangingStyle, setIsChangingStyle,
    alphaDebounceRef,
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen theme-app-bg transition-colors duration-300">
        {/* Header */}
        <header className="border-b py-4" style={{ borderColor: 'var(--border-color)' }}>
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between">
              {/* Logo */}
              <div>
                <h1 className="text-2xl font-bold" style={{ color: 'var(--accent-gold)' }}>
                  🎨 Neural Style Transfer
                </h1>
                <p className="theme-text-muted text-xs">Real Time Style Transfer</p>
              </div>

              {/* Nav */}
              <nav className="flex gap-1">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      isActive ? 'text-white shadow-md' : 'theme-panel theme-text-secondary hover:opacity-80'
                    }`
                  }
                  style={({ isActive }) => isActive ? { backgroundColor: 'var(--accent-blue)' } : {}}
                >
                  🎥 Live
                </NavLink>
                <NavLink
                  to="/photo"
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      isActive ? 'text-white shadow-md' : 'theme-panel theme-text-secondary hover:opacity-80'
                    }`
                  }
                  style={({ isActive }) => isActive ? { backgroundColor: 'var(--accent-blue)' } : {}}
                >
                  📸 Photo
                </NavLink>
              </nav>

              {/* Tema + durum */}
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex gap-2 text-xs">
                  <span className={`px-2 py-1 rounded-full ${isWsConnected ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-600'}`}>
                    {isWsConnected ? '🟢 WS' : '🟡 WS'}
                  </span>
                  <span className={`px-2 py-1 rounded-full ${isBackendOnline ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                    {isBackendOnline ? '🟢 API' : '🔴 API'}
                  </span>
                  {currentFPS > 0 && (
                    <span className={`px-2 py-1 rounded-full ${currentFPS >= targetFPS * 0.8 ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-600'}`}>
                      📊 {currentFPS} FPS
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium theme-panel theme-text-secondary hover:opacity-80 transition"
                >
                  {isDark ? '☀️' : '🌙'}
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Sayfalar */}
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<LivePage {...sharedProps} />} />
            <Route path="/photo" element={<PhotoProcessor isBackendOnline={isBackendOnline} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;