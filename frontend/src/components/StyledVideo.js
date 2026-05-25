import React, { useEffect, useState } from 'react';

const StyledVideo = ({
  imageUrl,
  isProcessing = false,
  fps = null,
  targetFPS = 10,
  styleName = 'Stylized',
  onTakePhoto,
  canTakePhoto = false,
}) => {
  const [isImageLoaded, setIsImageLoaded] = useState(false);

  useEffect(() => {
    setIsImageLoaded(false);
  }, [imageUrl]);

  const getFPSColor = () => {
    if (fps === null || fps === 0) return 'text-gray-400';
    if (fps >= targetFPS * 0.8) return 'text-green-400';
    if (fps >= targetFPS * 0.5) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="relative w-full max-w-3xl mx-auto">
      <div
        className="relative rounded-xl overflow-hidden shadow-xl"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="Stylized webcam frame"
            className={`w-full h-auto block transition-opacity duration-300 -scale-x-100 ${
              isImageLoaded ? 'opacity-100' : 'opacity-0'
            }`}
            onLoad={() => setIsImageLoaded(true)}
          />
        ) : (
          <div
            className="w-full aspect-video flex flex-col items-center justify-center"
            style={{ backgroundColor: 'var(--bg-secondary)' }}
          >
            <div className="text-6xl mb-4">🎨</div>
            <p className="theme-text-muted text-center px-4">
              {isProcessing
                ? 'Stylized image processing...'
                : 'Start style transfer to see output'}
            </p>
          </div>
        )}

        {/* Kompakt FPS — stil etiketi ile aynı boyut */}
        {fps !== null && fps > 0 && imageUrl && (
          <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1 text-xs text-white">
            <span className={`font-mono ${getFPSColor()}`}>
              {fps} / {targetFPS} FPS
            </span>
          </div>
        )}

        {isProcessing && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center pointer-events-none">
            <div className="bg-black/80 rounded-full p-3">
              <div
                className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
                style={{ borderColor: 'var(--accent-blue)', borderTopColor: 'transparent' }}
              />
            </div>
          </div>
        )}

        {imageUrl && (
          <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1 text-xs text-white max-w-[55%] truncate">
            {styleName}
          </div>
        )}
      </div>

      <div className="flex justify-center gap-3 mt-4 flex-wrap">
        <button
          type="button"
          onClick={onTakePhoto}
          disabled={!canTakePhoto || !imageUrl}
          className="px-4 py-2 rounded-full text-sm font-medium text-white transition disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90"
          style={{ backgroundColor: 'var(--accent-blue)' }}
          title="Download available stylized frame"
        >
          📸 Capture
        </button>
      </div>
    </div>
  );
};

export default StyledVideo;
