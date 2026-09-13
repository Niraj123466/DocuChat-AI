import React from 'react';

export function EmptyState({ onSelectPrompt }) {
  const starterPrompts = [
    {
      title: 'Summarize Key Findings',
      desc: 'Extract actionable insights, conclusions, and core arguments from documents.',
      icon: 'fa-regular fa-file-lines',
      prompt: 'What are the main technical findings and core arguments across the indexed documents?',
    },
    {
      title: 'Analyze Architecture & Pipeline',
      desc: 'Inspect LangGraph cyclic nodes, cross-encoders, and self-correcting reflection loops.',
      icon: 'fa-solid fa-arrows-spin',
      prompt: 'Explain how the LangGraph cyclic workflow and cross-encoder reranker operate in this system.',
    },
    {
      title: 'Verify Grounding & Citations',
      desc: 'Test factual evidence grounding, source tag attribution, and hallucination bounds.',
      icon: 'fa-solid fa-quote-left',
      prompt: 'Provide a detailed breakdown of the document with explicit citations for each claim.',
    },
  ];

  return (
    <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto px-4 text-center select-none animate-fadeIn">
      {/* Brand Badge */}
      <div className="h-12 w-12 rounded-xl bg-indigo-600/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-4 shadow-sm">
        <i className="fa-solid fa-terminal text-lg"></i>
      </div>

      <h2 className="text-base font-semibold text-white tracking-tight mb-1.5">
        DocuChat Technical Workspace
      </h2>
      <p className="text-xs text-slate-400 max-w-md mb-8 leading-relaxed">
        Query vectorized documents with cyclic state machines, neural cross-encoder reranking,
        deterministic citation grounding, and dual-layer safety guardrails.
      </p>

      {/* Starter Prompts */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 w-full text-left">
        {starterPrompts.map((item, i) => (
          <button
            key={i}
            onClick={() => onSelectPrompt(item.prompt)}
            className="p-3 rounded-lg bg-[#0e131f] hover:bg-[#161f30] border border-hairline hover:border-indigo-500/40 transition-fast group"
          >
            <div className="h-6 w-6 rounded bg-[#161f30] border border-hairline flex items-center justify-center text-indigo-400 text-xs mb-2 group-hover:scale-105 transition-fast">
              <i className={item.icon}></i>
            </div>
            <p className="text-xs font-semibold text-slate-200 mb-1">{item.title}</p>
            <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">{item.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
