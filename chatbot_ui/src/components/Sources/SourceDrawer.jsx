import React, { useEffect } from 'react';

export function SourceDrawer({ citation, onClose, onAskAboutSource }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!citation) return null;

  const scorePct = Math.round((citation.relevance_score || 0.9) * 100);

  return (
    <aside className="w-96 flex-shrink-0 border-l border-hairline bg-[#0e131f] flex flex-col h-full z-20 animate-fadeIn">
      {/* 1. Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-hairline bg-[#090d16]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/40">
            [Doc {citation.doc_index}]
          </span>
          <span className="text-xs font-medium text-slate-300">Grounding Evidence</span>
        </div>
        <div className="flex items-center gap-2">
          <kbd>Esc</kbd>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[#161f30] text-slate-400 hover:text-white transition-fast"
            title="Close Drawer"
          >
            <i className="fa-solid fa-xmark text-xs"></i>
          </button>
        </div>
      </div>

      {/* 2. Metadata Strip */}
      <div className="p-4 border-b border-hairline space-y-3 bg-[#0e131f]">
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-slate-500 font-semibold mb-1">
            Source Document
          </p>
          <div className="flex items-center gap-2 text-xs font-medium text-slate-200">
            <i className="fa-regular fa-file-pdf text-rose-400"></i>
            <span className="truncate">{citation.source}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-hairline">
          <div>
            <span className="text-[10px] text-slate-500 block">Cross-Encoder Match</span>
            <span className="font-mono text-xs font-semibold text-emerald-400">
              {scorePct}% ({Number(citation.relevance_score || 0.9).toFixed(3)})
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Location</span>
            <span className="font-mono text-xs text-slate-300">
              {citation.page_number ? `Page ${citation.page_number}` : 'Full Text'}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Text Passage Inspector */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <p className="text-[10px] uppercase font-mono tracking-wider text-slate-500 font-semibold">
          Retrieved Passage Excerpt
        </p>
        <div className="p-3.5 rounded-lg bg-[#090d16] border border-hairline text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap selection:bg-cyan-500/30 selection:text-cyan-200">
          {citation.text_snippet || 'No text snippet content available for this chunk.'}
        </div>
      </div>

      {/* 4. Footer Action */}
      <div className="p-3 border-t border-hairline bg-[#090d16]">
        <button
          onClick={() => onAskAboutSource(`What else is mentioned in ${citation.source} about this topic?`)}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded text-xs font-medium bg-[#161f30] hover:bg-[#1c273d] text-slate-200 border border-hairline transition-fast"
        >
          <i className="fa-regular fa-comment-dots text-indigo-400 text-xs"></i>
          <span>Ask About This Source</span>
        </button>
      </div>
    </aside>
  );
}
