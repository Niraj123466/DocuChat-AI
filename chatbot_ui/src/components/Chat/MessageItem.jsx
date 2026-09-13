import React, { useState } from 'react';

export function MessageItem({ message, onSelectCitation }) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null); // 'up' | 'down' | null

  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render markdown paragraphs, code blocks, lists, and inline citation pills
  const renderContent = (content) => {
    if (!content) return null;

    const lines = content.split('\n');
    let inCodeBlock = false;
    let codeContent = [];
    let codeLanguage = '';
    const elements = [];

    lines.forEach((line, index) => {
      // Code block start/end
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <div key={`code-${index}`} className="my-2.5 rounded border border-hairline bg-[#090d16] overflow-hidden">
              <div className="flex items-center justify-between px-3 py-1.5 bg-[#0e131f] border-b border-hairline text-[11px] font-mono text-slate-400">
                <span>{codeLanguage || 'text'}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(codeContent.join('\n'))}
                  className="hover:text-slate-200 transition-fast flex items-center gap-1"
                >
                  <i className="fa-regular fa-copy text-[10px]"></i> Copy
                </button>
              </div>
              <pre className="p-3 text-xs font-mono text-cyan-200 overflow-x-auto leading-relaxed">
                <code>{codeContent.join('\n')}</code>
              </pre>
            </div>
          );
          codeContent = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
          codeLanguage = line.trim().replace('```', '');
        }
        return;
      }

      if (inCodeBlock) {
        codeContent.push(line);
        return;
      }

      // Bullet items
      if (line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
        const itemText = line.trim().substring(2);
        elements.push(
          <li key={`li-${index}`} className="ml-4 list-disc text-slate-200 my-1 leading-relaxed text-xs">
            {formatInlineContent(itemText, message.citations, onSelectCitation)}
          </li>
        );
        return;
      }

      // Numbered lists
      const numberedMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
      if (numberedMatch) {
        elements.push(
          <li key={`ol-${index}`} className="ml-4 list-decimal text-slate-200 my-1 leading-relaxed text-xs">
            {formatInlineContent(numberedMatch[2], message.citations, onSelectCitation)}
          </li>
        );
        return;
      }

      // Empty line
      if (!line.trim()) {
        elements.push(<div key={`sp-${index}`} className="h-2" />);
        return;
      }

      // Regular paragraph
      elements.push(
        <p key={`p-${index}`} className="my-1.5 text-xs text-slate-200 leading-relaxed">
          {formatInlineContent(line, message.citations, onSelectCitation)}
        </p>
      );
    });

    return elements;
  };

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} py-2`}>
      {isUser ? (
        /* USER TURN */
        <div className="max-w-xl flex items-start gap-2.5">
          <div className="rounded-xl px-4 py-2.5 bg-[#161f30] border border-hairline text-slate-100 text-xs shadow-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
          <div className="h-6 w-6 rounded-md bg-slate-800 border border-hairline flex items-center justify-center text-[10px] font-semibold text-slate-300 flex-shrink-0 mt-0.5">
            U
          </div>
        </div>
      ) : (
        /* ASSISTANT TURN */
        <div className="max-w-3xl w-full flex items-start gap-3">
          <div className="h-7 w-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 flex-shrink-0 mt-1">
            <i className="fa-solid fa-sparkles text-xs"></i>
          </div>

          <div className="flex-1 min-w-0">
            {/* Assistant Body */}
            <div className="text-slate-100 text-xs">{renderContent(message.content)}</div>

            {/* Grounding Source Pills (Evidence Row) */}
            {message.citations && message.citations.length > 0 && (
              <div className="mt-3 pt-2.5 border-t border-hairline">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="text-[10px] font-mono uppercase text-slate-500 font-semibold tracking-wider">
                    Grounded Sources ({message.citations.length})
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {message.citations.map((cite, cIdx) => (
                    <button
                      key={cIdx}
                      onClick={() => onSelectCitation && onSelectCitation(cite)}
                      className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-[#0e131f] hover:bg-[#161f30] border border-hairline hover:border-cyan-500/40 text-[11px] text-slate-300 font-mono transition-fast group"
                      title="Inspect Grounded Source Passage"
                    >
                      <span className="text-cyan-400 font-semibold">[Doc {cite.doc_index}]</span>
                      <span className="truncate max-w-[140px] text-slate-400 group-hover:text-slate-200">
                        {cite.source}
                      </span>
                      <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {Math.round((cite.relevance_score || 0.9) * 100)}%
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Instrument Footer / Actions */}
            <div className="mt-2.5 pt-1.5 flex items-center justify-between text-[10px] font-mono text-slate-500">
              <div className="flex items-center gap-2">
                {message.metadata?.cache_hit ? (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <i className="fa-solid fa-bolt text-[8px]"></i> 2ms Cache Hit
                  </span>
                ) : (
                  message.metadata?.llm_latency_ms && (
                    <span className="px-1.5 py-0.5 rounded bg-[#0e131f] border border-hairline text-slate-400">
                      ⚡ {message.metadata.llm_latency_ms}ms
                    </span>
                  )
                )}

                {message.retryCount > 0 && (
                  <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    🔄 {message.retryCount} Reflect
                  </span>
                )}

                <span className="px-1.5 py-0.5 rounded bg-[#0e131f] border border-hairline text-slate-400 flex items-center gap-1">
                  <i className="fa-solid fa-shield-halved text-emerald-400 text-[8px]"></i> Grounded
                </span>
              </div>

              {/* Utility actions */}
              <div className="flex items-center gap-1 opacity-60 hover:opacity-100 transition-fast">
                <button
                  onClick={handleCopy}
                  className="p-1 hover:text-slate-200 transition-fast"
                  title="Copy message text"
                >
                  <i className={`fa-regular ${copied ? 'fa-check text-emerald-400' : 'fa-copy'} text-[10px]`}></i>
                </button>
                <button
                  onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                  className={`p-1 hover:text-slate-200 transition-fast ${feedback === 'up' ? 'text-indigo-400' : ''}`}
                  title="Helpful response"
                >
                  <i className="fa-regular fa-thumbs-up text-[10px]"></i>
                </button>
                <button
                  onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                  className={`p-1 hover:text-slate-200 transition-fast ${feedback === 'down' ? 'text-rose-400' : ''}`}
                  title="Report issue"
                >
                  <i className="fa-regular fa-thumbs-down text-[10px]"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper to convert inline markdown like **bold**, `code`, and [Doc 1] into React elements
function formatInlineContent(text, citations, onSelectCitation) {
  if (!text) return text;

  // Match: bold, inline code, or citation tags [Doc X] or [X]
  const regex = /(\*\*.*?\*\*|`.*?`|\[Doc\s*\d+\]|\[\d+\])/g;
  const parts = text.split(regex);

  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-indigo-300">
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} className="px-1.5 py-0.5 rounded bg-[#0e131f] text-cyan-300 font-mono text-[11px] border border-hairline">
          {part.slice(1, -1)}
        </code>
      );
    }

    // Inline Citation Pill: [Doc 1] or [1]
    const docMatch = part.match(/^\[(?:Doc\s*)?(\d+)\]$/i);
    if (docMatch) {
      const docIndex = parseInt(docMatch[1], 10);
      const matchedCite = citations?.find((c) => c.doc_index === docIndex);
      return (
        <button
          key={i}
          onClick={() => matchedCite && onSelectCitation && onSelectCitation(matchedCite)}
          className="inline-flex items-center px-1 py-0.2 mx-0.5 rounded bg-cyan-950/40 hover:bg-cyan-900/60 border border-cyan-800/40 text-[10px] font-mono text-cyan-300 transition-fast cursor-pointer"
          title={matchedCite ? `Source: ${matchedCite.source} (${Math.round((matchedCite.relevance_score || 0.9) * 100)}% Match)` : 'Citation'}
        >
          {part}
        </button>
      );
    }

    return part;
  });
}
