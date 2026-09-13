import React from 'react';

export function StatusBar({ apiOnline, telemetryData, onOpenCommandPalette }) {
  return (
    <footer className="h-6 px-4 bg-[#090d16] border-t border-hairline flex items-center justify-between text-[10px] font-mono text-slate-500 select-none flex-shrink-0 z-10">
      {/* Left: Model & System Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              apiOnline ? 'bg-emerald-400 animate-subtle-pulse' : 'bg-rose-500'
            }`}
          ></span>
          <span className="text-slate-400">{apiOnline ? 'FastAPI ASGI Live' : 'Offline'}</span>
        </div>

        <span className="text-slate-700">|</span>

        <span className="text-slate-400">Model: Gemini 2.5 Flash</span>

        <span className="text-slate-700 hidden sm:inline">|</span>

        <span className="text-slate-400 hidden sm:inline">Reranker: BAAI/bge-reranker-base</span>
      </div>

      {/* Right: Telemetry & Shortcuts */}
      <div className="flex items-center gap-3">
        <span className="hidden md:inline">
          Cache: <span className="text-cyan-400">{telemetryData.cacheHitRatio || 64}% Hits</span>
        </span>

        <span className="text-slate-700 hidden md:inline">|</span>

        <button
          onClick={onOpenCommandPalette}
          className="hover:text-slate-300 transition-fast flex items-center gap-1"
        >
          <span>Command Palette</span>
          <kbd>⌘K</kbd>
        </button>
      </div>
    </footer>
  );
}
