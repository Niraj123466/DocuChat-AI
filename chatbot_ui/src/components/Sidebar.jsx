import React, { useState } from 'react';

export function Sidebar({
  conversations,
  activeConvId,
  activeTab,
  documentsCount,
  apiOnline,
  user,
  isAuthenticated,
  onLogout,
  onOpenAuthModal,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onSelectTab,
  onOpenCommandPalette,
  isCollapsed,
  onToggleCollapse,
}) {
  const [filterQuery, setFilterQuery] = useState('');

  const filteredConversations = conversations.filter((c) =>
    (c.title || 'Untitled Thread').toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <aside
      className={`h-full flex flex-col border-r border-hairline bg-[#0e131f] transition-all duration-200 z-30 select-none ${
        isCollapsed ? 'w-16' : 'w-72'
      }`}
    >
      {/* 1. Header: Brand & Status */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-hairline">
        {!isCollapsed && (
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <i className="fa-solid fa-brain text-sm"></i>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs tracking-tight text-white">DocuChat-AI</span>
                <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  v2.0
                </span>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    apiOnline ? 'bg-emerald-400 animate-subtle-pulse' : 'bg-rose-500'
                  }`}
                ></span>
                <span className="text-[10px] text-slate-400">
                  {apiOnline ? 'Gateway Live' : 'Connecting...'}
                </span>
              </div>
            </div>
          </div>
        )}

        {isCollapsed && (
          <div className="mx-auto h-8 w-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <i className="fa-solid fa-brain text-sm"></i>
          </div>
        )}

        <button
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          className="p-1.5 rounded hover:bg-[#161f30] text-slate-400 hover:text-slate-200 transition-fast"
        >
          <i className={`fa-solid ${isCollapsed ? 'fa-angles-right' : 'fa-angles-left'} text-xs`}></i>
        </button>
      </div>

      {/* 2. Action: New Conversation & Command Search */}
      <div className="p-3 space-y-2 border-b border-hairline">
        <button
          onClick={onNewConversation}
          className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-fast shadow-sm ${
            isCollapsed ? 'px-0' : ''
          }`}
          title="New Thread (⌘N)"
        >
          <i className="fa-solid fa-plus text-xs"></i>
          {!isCollapsed && (
            <span className="flex items-center justify-between flex-1">
              <span>New Thread</span>
              <kbd className="text-[9px] bg-indigo-700 border-indigo-500 text-indigo-100">⌘N</kbd>
            </span>
          )}
        </button>

        {!isCollapsed && (
          <button
            onClick={onOpenCommandPalette}
            className="w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs bg-[#090d16] border border-hairline text-slate-400 hover:text-slate-200 hover:border-slate-700 transition-fast"
          >
            <span className="flex items-center gap-2">
              <i className="fa-solid fa-magnifying-glass text-[10px]"></i>
              <span>Quick jump...</span>
            </span>
            <kbd>⌘K</kbd>
          </button>
        )}
      </div>

      {/* 3. Primary Navigation Sections */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-5">
        {/* Section: Views */}
        <div className="space-y-0.5">
          {!isCollapsed && (
            <p className="px-2 text-[10px] uppercase font-mono tracking-wider text-slate-500 font-semibold mb-1">
              Workbench
            </p>
          )}

          <button
            onClick={() => onSelectTab('chat')}
            className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs font-medium transition-fast ${
              activeTab === 'chat'
                ? 'bg-[#161f30] text-indigo-300 border border-slate-700/60'
                : 'text-slate-400 hover:bg-[#161f30]/60 hover:text-slate-200'
            } ${isCollapsed ? 'justify-center px-0' : ''}`}
            title="Chat Interface"
          >
            <i className="fa-regular fa-message text-xs w-4 text-center"></i>
            {!isCollapsed && <span>Conversation</span>}
          </button>

          <button
            onClick={() => onSelectTab('documents')}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs font-medium transition-fast ${
              activeTab === 'documents'
                ? 'bg-[#161f30] text-indigo-300 border border-slate-700/60'
                : 'text-slate-400 hover:bg-[#161f30]/60 hover:text-slate-200'
            } ${isCollapsed ? 'justify-center px-0' : ''}`}
            title="Knowledge Base Documents"
          >
            <span className="flex items-center gap-2.5 truncate">
              <i className="fa-regular fa-folder-open text-xs w-4 text-center"></i>
              {!isCollapsed && <span>Knowledge Base</span>}
            </span>
            {!isCollapsed && (
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#090d16] border border-hairline text-slate-400">
                {documentsCount}
              </span>
            )}
          </button>

          <button
            onClick={() => onSelectTab('intelligence')}
            className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs font-medium transition-fast ${
              activeTab === 'intelligence'
                ? 'bg-[#161f30] text-indigo-300 border border-slate-700/60'
                : 'text-slate-400 hover:bg-[#161f30]/60 hover:text-slate-200'
            } ${isCollapsed ? 'justify-center px-0' : ''}`}
            title="Evaluation & Observability"
          >
            <i className="fa-solid fa-chart-simple text-xs w-4 text-center"></i>
            {!isCollapsed && <span>Observability & Eval</span>}
          </button>
        </div>

        {/* Section: Conversation Threads */}
        {!isCollapsed && (
          <div className="space-y-1">
            <div className="flex items-center justify-between px-2 text-[10px] uppercase font-mono tracking-wider text-slate-500 font-semibold mb-1">
              <span>Threads</span>
              <span className="text-[9px] text-slate-500">{conversations.length}</span>
            </div>

            {conversations.length > 5 && (
              <div className="px-1 mb-1">
                <input
                  type="text"
                  placeholder="Filter threads..."
                  value={filterQuery}
                  onChange={(e) => setFilterQuery(e.target.value)}
                  className="w-full bg-[#090d16] border border-hairline rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            <div className="space-y-0.5 max-h-60 overflow-y-auto pr-0.5">
              {filteredConversations.length === 0 ? (
                <p className="px-2 py-3 text-[11px] text-slate-500 italic">No threads found.</p>
              ) : (
                filteredConversations.map((c) => {
                  const isActive = activeConvId === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => onSelectConversation(c.id)}
                      className={`group flex items-center justify-between px-2.5 py-1.5 rounded text-xs cursor-pointer transition-fast ${
                        isActive
                          ? 'bg-[#161f30] text-white border border-indigo-500/30'
                          : 'text-slate-400 hover:bg-[#161f30]/50 hover:text-slate-200 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <i className={`fa-regular fa-comment-dots text-[10px] ${isActive ? 'text-indigo-400' : 'opacity-40'}`}></i>
                        <span className="truncate font-medium text-[11px]">{c.title || 'Untitled Session'}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversation(c.id);
                        }}
                        title="Delete Thread"
                        className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-slate-500 transition-fast"
                      >
                        <i className="fa-regular fa-trash-can text-[10px]"></i>
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Tenant User Profile */}
      <div className="p-3 border-t border-hairline bg-[#090d16]/70">
        {!isCollapsed ? (
          isAuthenticated && user ? (
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-bold text-white text-[11px] shrink-0 shadow-sm shadow-cyan-500/10">
                  {(user.name || user.email || 'U')[0].toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-medium text-slate-200 truncate">{user.name || user.email.split('@')[0]}</span>
                    <span className="text-[9px] uppercase tracking-wider px-1 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">
                      {user.role || 'User'}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 truncate">{user.email}</p>
                </div>
              </div>
              <button
                onClick={onLogout}
                title="Sign Out"
                className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 rounded-lg transition-colors shrink-0"
              >
                <i className="fa-solid fa-arrow-right-from-bracket text-xs"></i>
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuthModal}
              className="w-full py-1.5 px-3 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 hover:from-cyan-600/30 hover:to-blue-600/30 border border-cyan-500/30 text-cyan-300 rounded-xl text-xs font-medium flex items-center justify-center gap-2 transition-all shadow-sm"
            >
              <i className="fa-solid fa-user-lock text-[11px]"></i>
              <span>Sign In / Register</span>
            </button>
          )
        ) : (
          <div className="flex justify-center">
            {isAuthenticated ? (
              <button
                onClick={onLogout}
                title={`Signed in as ${user?.email}. Click to Sign Out`}
                className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-bold text-white text-[11px]"
              >
                {(user?.name || user?.email || 'U')[0].toUpperCase()}
              </button>
            ) : (
              <button
                onClick={onOpenAuthModal}
                title="Sign In"
                className="w-7 h-7 rounded-lg bg-slate-800 text-cyan-400 flex items-center justify-center text-xs hover:bg-slate-700 transition-colors"
              >
                <i className="fa-solid fa-user-lock text-[11px]"></i>
              </button>
            )}
          </div>
        )}
      </div>

      {/* 4. Footer System Info */}
      <div className="p-3 border-t border-hairline bg-[#090d16] text-[11px] text-slate-400">
        {!isCollapsed ? (
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
              <span className="text-[10px] font-mono text-slate-400">LangGraph 0.6</span>
            </span>
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-slate-400 hover:text-indigo-300 transition-fast flex items-center gap-1 text-[10px] font-mono"
            >
              Docs <i className="fa-solid fa-arrow-up-right-from-square text-[8px]"></i>
            </a>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" title="LangGraph 0.6 Active"></span>
          </div>
        )}
      </div>
    </aside>
  );
}
