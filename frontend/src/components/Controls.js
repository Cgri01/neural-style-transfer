import React, { useEffect, useState } from 'react';
import { getStyles } from '../api';

const Controls = ({
  isStreaming,
  onToggleStreaming,
  alpha = 0.7,
  onAlphaChange,
  fps = 8,
  onFpsChange,
  isBackendReady,
  isBackendOnline = false,
  currentStyle = 'starry_night',
  onStyleChange,
  isChangingStyle = false,
  processSize = 384,
  onProcessSizeChange,
}) => {
  const [availableStyles, setAvailableStyles] = useState([]);
  const [isLoadingStyles, setIsLoadingStyles] = useState(false);

  // Stil listesini backend'den al (WebSocket baglantisini bekleme)
  useEffect(() => {
    const loadStyles = async () => {
      setIsLoadingStyles(true);
      try {
        const data = await getStyles();
        setAvailableStyles(data.available_styles || []);
      } catch (error) {
        console.error('Style list could not load:', error);
        setAvailableStyles([
          {
            id: 'starry_night',
            name: '🌙 Van Gogh - Starry Night',
            description: 'Abstract brush strokes',
            is_available: true,
          },
          {
            id: 'candy',
            name: '🍬 Candy Style',
            description: 'Vibrant Colors',
            is_available: true,
          },
          {
            id: 'mosaic',
            name: '🔲 Mosaic Style',
            description: 'mosaic texture',
            is_available: true,
          },
          {
            id: 'rain_princess',
            name: '🌧️ Rain Princess',
            description: 'Impressionist tones',
            is_available: true,
          },
          {
            id: 'udnie',
            name: '🎨 Udnie',
            description: 'Pastel-Abstract',
            is_available: true,
          },
        ]);
      } finally {
        setIsLoadingStyles(false);
      }
    };

    loadStyles();
  }, [isBackendOnline]);

  const handleStyleChangeLocal = (e) => {
    const newStyleId = e.target.value;
    if (onStyleChange && newStyleId !== currentStyle) {
      onStyleChange(newStyleId);
    }
  };

  const handleAlphaChange = (e) => {
    const newAlpha = parseFloat(e.target.value);
    if (onAlphaChange) onAlphaChange(newAlpha);
  };

  const handleFpsChange = (e) => {
    const newFps = parseInt(e.target.value, 10);
    if (onFpsChange) onFpsChange(newFps);
  };

  const getAlphaDescription = (value) => {
    if (value >= 0.9) return 'Fast reaction (it might be tremor)';
    if (value >= 0.7) return 'Stable (Advanced)';
    if (value >= 0.5) return 'Smooth transitions';
    return 'Very smooth (delayed)';
  };

  const getFpsDescription = (value) => {
    if (value >= 15) return 'Smooth';
    if (value >= 10) return 'Good Balance';
    if (value >= 5) return 'Acceptable';
    return 'low fluency';
  };

  const currentStyleInfo = availableStyles.find((s) => s.id === currentStyle);

  return (
    <div className="theme-panel rounded-2xl p-5 w-full max-w-md mx-auto">
      <h3
        className="text-lg font-semibold text-center mb-4"
        style={{ color: 'var(--accent-blue)' }}
      >
        Controller
      </h3>

      <div className="space-y-5">
        <div>
          <label className="block text-sm font-medium theme-text-secondary mb-3">
            Style Transfer
          </label>
          <button
            type="button"
            onClick={onToggleStreaming}
            disabled={!isBackendReady}
            className={`w-full py-3 rounded-xl font-medium transition-all transform hover:scale-[1.02] ${
              isStreaming
                ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30'
                : 'text-white shadow-lg shadow-blue-500/30'
            } disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100`}
            style={!isStreaming ? { backgroundColor: 'var(--accent-blue)' } : undefined}
          >
            {isStreaming ? '⏸️ Stop Style Transfer' : '▶️ Start Style Transfer'}
          </button>
          {!isBackendReady && (
            <p className="text-xs text-red-400 mt-1 text-center">
              Backend closed or connecting...
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium theme-text-secondary mb-2">
            🎨 Style Choosing
          </label>
          <select
            value={currentStyle}
            onChange={handleStyleChangeLocal}
            disabled={!isBackendReady || isLoadingStyles || isChangingStyle}
            className="w-full px-4 py-2 theme-input border rounded-lg focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50"
          >
            {availableStyles.map((style) => (
              <option key={style.id} value={style.id} disabled={!style.is_available}>
                {style.name} {!style.is_available && '(Soon)'}
              </option>
            ))}
          </select>
          {isLoadingStyles && (
            <p className="text-xs theme-text-muted mt-1">Styles loading...</p>
          )}
          {isChangingStyle && (
            <p className="text-xs theme-text-muted mt-1">Style changing...</p>
          )}
          {currentStyleInfo?.description && (
            <p className="text-xs theme-text-muted mt-1">
               {currentStyleInfo.description}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium theme-text-secondary mb-2">
            🖼️ Processing Resolution
          </label>
          <select
            value={processSize}
            onChange={(e) => {
              if (onProcessSizeChange) {
                onProcessSizeChange(parseInt(e.target.value, 10));
              }
            }}
            disabled={!isBackendReady}
            className="w-full px-4 py-2 theme-input border rounded-lg disabled:opacity-50"
          >
            <option value={256}>256x256 - Fast (Low Quality)</option>
            <option value={384}>384x384 - Balanced (Advanced)</option>
            <option value={512}>512x512 - High Quality (Slow)</option>
          </select>
          <p className="text-xs theme-text-muted mt-1">
             When it's changed, websocket connect again
          </p>
          
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium theme-text-secondary">
              🎚️ Temporal Filter (Alpha)
            </label>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ color: 'var(--accent-blue)', backgroundColor: 'color-mix(in srgb, var(--accent-blue) 20%, transparent)' }}
            >
              {alpha.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min="0.3"
            max="0.95"
            step="0.01"
            value={alpha}
            onChange={handleAlphaChange}
            disabled={!isBackendReady}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
            style={{ accentColor: 'var(--accent-blue)' }}
          />
          <div className="flex justify-between text-xs theme-text-muted mt-1">
            <span>Softer</span>
            <span>{getAlphaDescription(alpha)}</span>
            <span>More fast</span>
          </div>
          <p className="text-xs theme-text-muted mt-0.5">
             Alpha low = smoother response, High = faster response
          </p>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium theme-text-secondary">Target FPS</label>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ color: 'var(--accent-blue)', backgroundColor: 'color-mix(in srgb, var(--accent-blue) 20%, transparent)' }}
            >
              {fps} FPS
            </span>
          </div>
          <input
            type="range"
            min="3"
            max="20"
            step="1"
            value={fps}
            onChange={handleFpsChange}
            disabled={!isBackendReady}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
            style={{ accentColor: 'var(--accent-blue)' }}
          />
          <div className="flex justify-between text-xs theme-text-muted mt-1">
            <span>Less (3 FPS)</span>
            <span>{getFpsDescription(fps)}</span>
            <span>More (20 FPS)</span>
          </div>
        </div>

        <div className="theme-info-box rounded-lg p-3 mt-2">
          <div className="flex flex-wrap items-center gap-2 text-xs theme-text-muted">
            <span>🟢 Alpha: <strong style={{ color: 'var(--accent-blue)' }}>{alpha.toFixed(2)}</strong></span>
            <span>•</span>
            <span>🎯 FPS: <strong style={{ color: 'var(--accent-blue)' }}>{fps}</strong></span>
            <span>•</span>
            <span>🎨 {currentStyleInfo?.name || currentStyle}</span>
            <span>•</span>
            <span>📐 {processSize}px</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Controls;
