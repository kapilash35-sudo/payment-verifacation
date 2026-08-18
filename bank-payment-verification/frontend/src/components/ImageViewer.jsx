import React, { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize, Image, Flame } from 'lucide-react';

function pathToUrl(filePath) {
  if (!filePath) return null;
  const filename = filePath.split('\\').pop().split('/').pop();
  return `http://localhost:8000/static/${filename}`;
}

function ImageViewer({ imagePath, elaImagePath, elaScore, ocrBoxes }) {
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [viewMode, setViewMode] = useState('original');

  const imageUrl = pathToUrl(imagePath);
  const elaUrl = pathToUrl(elaImagePath);
  const displayUrl = viewMode === 'ela' && elaUrl ? elaUrl : imageUrl;
  const showOcr = viewMode === 'original';

  const [imgSize, setImgSize] = useState({ w: 1, h: 1 });

  const isSuspicious = elaScore != null && elaScore > 40;
  const elaBadgeClass = isSuspicious
    ? 'bg-red-100 text-red-700 border-red-200'
    : 'bg-green-100 text-green-700 border-green-200';

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY * -0.001;
    setScale((prev) => Math.min(Math.max(0.5, prev + delta), 4));
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-2 px-2 gap-2 flex-wrap">
        <h3 className="text-sm font-semibold text-gray-700">Payment Slip Evidence</h3>
        <div className="flex items-center gap-2">
          {elaScore != null && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium border flex items-center gap-1 ${elaBadgeClass}`}
              title="Error Level Analysis — detects Photoshop tampering"
            >
              <Flame size={12} />
              ELA: {elaScore.toFixed(1)} {isSuspicious ? '⚠️' : '✓'}
            </span>
          )}
          {elaUrl && (
            <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs">
              <button
                onClick={() => { setViewMode('original'); resetView(); }}
                className={`px-2 py-1 flex items-center gap-1 transition-colors ${
                  viewMode === 'original' ? 'bg-blue-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Image size={14} /> Original
              </button>
              <button
                onClick={() => { setViewMode('ela'); resetView(); }}
                className={`px-2 py-1 flex items-center gap-1 transition-colors ${
                  viewMode === 'ela' ? 'bg-orange-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Flame size={14} /> ELA Heatmap
              </button>
            </div>
          )}
          <button
            onClick={() => setScale((s) => Math.min(s + 0.2, 4))}
            className="p-1 hover:bg-gray-200 rounded text-gray-600"
          >
            <ZoomIn size={18} />
          </button>
          <button
            onClick={() => setScale((s) => Math.max(s - 0.2, 0.5))}
            className="p-1 hover:bg-gray-200 rounded text-gray-600"
          >
            <ZoomOut size={18} />
          </button>
          <button onClick={resetView} className="p-1 hover:bg-gray-200 rounded text-gray-600">
            <Maximize size={18} />
          </button>
        </div>
      </div>

      {viewMode === 'ela' && (
        <p className="text-xs text-orange-700 bg-orange-50 px-3 py-1 rounded mb-2 mx-2">
          Bright spots indicate areas with different compression — possible digital editing
        </p>
      )}

      <div
        className="flex-1 bg-gray-200 rounded-lg overflow-hidden relative cursor-grab active:cursor-grabbing border border-gray-300 shadow-inner"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div
          className="absolute inset-0 flex items-center justify-center transition-transform duration-75"
          style={{ transform: `translate(${position.x}px, ${position.y}px) scale(${scale})` }}
        >
          <div className="relative">
            <img
              src={displayUrl}
              alt={viewMode === 'ela' ? 'ELA Heatmap' : 'Payment Slip'}
              className="max-h-[80vh] w-auto drop-shadow-lg"
              draggable="false"
              onLoad={(e) => setImgSize({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
            />
            {showOcr &&
              ocrBoxes &&
              ocrBoxes.map((ocr, i) => {
                const box = ocr.box;
                const x1 = Math.min(...box.map((p) => p[0]));
                const y1 = Math.min(...box.map((p) => p[1]));
                const x2 = Math.max(...box.map((p) => p[0]));
                const y2 = Math.max(...box.map((p) => p[1]));
                const left = (x1 / imgSize.w) * 100;
                const top = (y1 / imgSize.h) * 100;
                const width = ((x2 - x1) / imgSize.w) * 100;
                const height = ((y2 - y1) / imgSize.h) * 100;

                return (
                  <div
                    key={i}
                    className="absolute border-2 border-yellow-400 bg-yellow-400/20 hover:bg-yellow-400/40 transition-colors"
                    style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
                    title={`${ocr.text} (${Math.round(ocr.confidence * 100)}%)`}
                  />
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ImageViewer;
