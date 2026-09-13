import React, { useState, useEffect, useRef } from 'react';

export function CommandPalette({
  isOpen,
  onClose,
  conversations,
  onSelectConversation,
  onNewConversation,
  onSelectTab,
  onTriggerUpload,
}) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Build command options list
  const baseActions = [
    { id: 'new-thread', title: 'New Conversation Thread', icon: 'fa-solid fa-plus', hotkey: '⌘N', action: onNewConversation },
    { id: 'tab-chat', title: 'Go to Chat Worksurface', icon: 'fa-regular fa-message', hotkey: '⌘1', action: () => onSelectTab('chat') },
    { id: 'tab-docs', title: 'Open Knowledge Base Documents', icon: 'fa-regular fa-folder-open', hotkey: '⌘2', action: () => onSelectTab('documents') },
    { id: 'tab-intel', title: 'Inspect Metrics & Evaluation Scorecard', icon: 'fa-solid fa-chart-line', hotkey: '⌘3', action: () => onSelectTab('intelligence') },
    { id: 'upload-doc', title: 'Upload & Index PDF Document', icon: 'fa-solid fa-cloud-arrow-up', hotkey: '⌘U', action: onTriggerUpload },
  ];

  const threadItems = conversations.map((c) => ({
    id: `conv-${c.id}`,
    title: c.title || 'Untitled Thread',
    icon: 'fa-regular fa-comment-dots',
    hotkey: 'Jump',
    action: () => onSelectConversation(c.id),
  }));

  const allItems = [...baseActions, ...threadItems].filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, allItems.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + allItems.length) % Math.max(1, allItems.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (allItems[selectedIndex]) {
        allItems[selectedIndex].action();
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/70 backdrop-blur-sm animate-fadeIn select-none"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl rounded-xl bg-[#161f30] border border-white/10 shadow-2xl overflow-hidden animate-slideDown"
      >
        {/* Search Input */}
        <div className="flex items-center px-4 py-3 border-b border-hairline bg-[#0e131f]">
          <span className="text-indigo-400 font-mono font-bold mr-2.5 text-sm">&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search threads..."
            className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none"
          />
          <kbd>Esc</kbd>
        </div>

        {/* Command Items List */}
        <div className="max-h-72 overflow-y-auto p-2 space-y-0.5">
          {allItems.length === 0 ? (
            <p className="p-4 text-center text-xs text-slate-500 italic">No matching commands found.</p>
          ) : (
            allItems.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    item.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2 rounded text-xs cursor-pointer transition-fast ${
                    isSelected ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-[#0e131f]'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <i className={`${item.icon} text-xs ${isSelected ? 'text-white' : 'text-slate-400'} w-4 text-center`}></i>
                    <span className="truncate font-medium">{item.title}</span>
                  </div>
                  <kbd className={isSelected ? 'bg-indigo-700 border-indigo-500 text-white' : ''}>
                    {item.hotkey}
                  </kbd>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
