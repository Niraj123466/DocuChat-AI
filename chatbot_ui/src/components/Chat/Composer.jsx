import React, { useState, useRef, useEffect } from 'react';

export function Composer({
  onSendMessage,
  onUploadFile,
  isLoading,
  loadingStep,
  activeDocumentCount,
}) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSendMessage(text);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    // Send on Cmd+Enter / Ctrl+Enter or single Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onUploadFile(file);
      e.target.value = '';
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4">
      {/* 1. Reasoning Status Banner (when inference is underway) */}
      {isLoading && (
        <div className="mb-2 flex items-center gap-2.5 px-3 py-1.5 rounded bg-[#0e131f] border border-hairline text-xs">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
          </span>
          <span className="font-mono text-indigo-300 text-[11px]">{loadingStep || 'Executing workflow...'}</span>
        </div>
      )}

      {/* 2. Main Composer Box */}
      <div className="rounded-xl bg-[#0e131f] border border-hairline focus-within:border-indigo-500/70 transition-fast shadow-lg overflow-hidden">
        {/* Text Input Area */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your documents... (Press Enter to send)"
          rows={1}
          disabled={isLoading}
          className="w-full px-3.5 pt-3 pb-2 bg-transparent text-xs text-slate-100 placeholder-slate-500 resize-none focus:outline-none leading-relaxed"
        />

        {/* Action Controls Toolbar */}
        <div className="px-3 pb-2.5 pt-1 flex items-center justify-between border-t border-hairline/60 text-xs">
          {/* Left Controls: File Attachment & Model Indicator */}
          <div className="flex items-center gap-1.5">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.txt,.docx"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="p-1.5 rounded hover:bg-[#161f30] text-slate-400 hover:text-slate-200 transition-fast flex items-center gap-1"
              title="Attach PDF Document to Knowledge Base"
            >
              <i className="fa-solid fa-paperclip text-xs"></i>
              <span className="text-[10px] font-mono hidden sm:inline text-slate-400">Attach</span>
            </button>

            <span className="h-3 w-px bg-hairline"></span>

            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#090d16] border border-hairline text-[10px] font-mono text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
              <span>Gemini 2.5 Flash + BAAI Reranker</span>
            </div>
          </div>

          {/* Right Controls: Send Button & Keyboard Shortcut Hint */}
          <div className="flex items-center gap-2">
            <kbd className="hidden sm:inline-flex">Enter</kbd>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !text.trim()}
              className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:bg-[#161f30] disabled:text-slate-600 text-white font-medium text-xs transition-fast flex items-center gap-1.5 shadow-sm active:scale-95"
            >
              <span>Send</span>
              <i className="fa-solid fa-arrow-up text-[10px]"></i>
            </button>
          </div>
        </div>
      </div>

      {/* 3. Subtle Privacy & Grounding Disclaimer */}
      <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-500 px-1 font-mono">
        <span className="flex items-center gap-1">
          <i className="fa-solid fa-shield-halved text-emerald-400 text-[9px]"></i>
          <span>OWASP LLM Guardrails Enabled</span>
        </span>
        <span>{activeDocumentCount} Active Document{activeDocumentCount !== 1 ? 's' : ''}</span>
      </div>
    </div>
  );
}
