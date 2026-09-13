import React, { useRef, useEffect } from 'react';
import { MessageItem } from './MessageItem';
import { Composer } from './Composer';
import { EmptyState } from './EmptyState';

export function ChatView({
  messages,
  activeConvId,
  conversations,
  isLoading,
  loadingStep,
  errorBanner,
  onDismissError,
  onSendMessage,
  onUploadFile,
  onSelectCitation,
  activeDocumentCount,
  onNewConversation,
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const activeTitle =
    conversations.find((c) => c.id === activeConvId)?.title || 'New Inquiry';

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#090d16]">
      {/* 1. Header Navigation Bar */}
      <header className="h-14 px-6 flex items-center justify-between border-b border-hairline bg-[#0e131f] flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-2 w-2 rounded-full bg-indigo-500 flex-shrink-0"></div>
          <h2 className="text-xs font-semibold text-slate-200 truncate">{activeTitle}</h2>
          <span className="h-3 w-px bg-hairline"></span>
          <span className="text-[11px] font-mono text-slate-500">
            {messages.length} Turn{messages.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={onNewConversation}
              className="px-2.5 py-1 rounded text-xs text-slate-400 hover:text-slate-200 hover:bg-[#161f30] transition-fast flex items-center gap-1.5"
              title="Start New Thread"
            >
              <i className="fa-solid fa-plus text-[10px]"></i>
              <span className="text-[11px]">New</span>
            </button>
          )}

          <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#161f30] border border-hairline text-[10px] font-mono text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
            <span>Grounded RAG</span>
          </div>
        </div>
      </header>

      {/* 2. Security Guardrail or Error Banner */}
      {errorBanner && (
        <div className="mx-6 mt-3 p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 text-rose-300 text-xs flex items-center justify-between shadow-sm animate-fadeIn">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-shield-halved text-rose-400 text-xs"></i>
            <span className="font-mono text-[11px]">{errorBanner}</span>
          </div>
          <button onClick={onDismissError} className="text-rose-400 hover:text-rose-200 transition-fast">
            <i className="fa-solid fa-xmark text-xs"></i>
          </button>
        </div>
      )}

      {/* 3. Message Stream Scroll Canvas */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.length === 0 ? (
          <EmptyState onSelectPrompt={onSendMessage} />
        ) : (
          messages.map((msg, i) => (
            <MessageItem
              key={msg.id || i}
              message={msg}
              onSelectCitation={onSelectCitation}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 4. AI Composer Dock */}
      <div className="flex-shrink-0">
        <Composer
          onSendMessage={onSendMessage}
          onUploadFile={onUploadFile}
          isLoading={isLoading}
          loadingStep={loadingStep}
          activeDocumentCount={activeDocumentCount}
        />
      </div>
    </div>
  );
}
