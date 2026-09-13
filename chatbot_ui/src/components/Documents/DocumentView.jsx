import React, { useState, useRef } from 'react';

export function DocumentView({
  documents,
  onUploadFile,
  uploadProgress,
  onAskAboutDoc,
}) {
  const [searchFilter, setSearchFilter] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const filteredDocs = documents.filter((doc) =>
    (doc.filename || '').toLowerCase().includes(searchFilter.toLowerCase())
  );

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer?.files;
    if (files && files[0]) {
      onUploadFile(files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#090d16]">
      {/* 1. Header */}
      <header className="h-14 px-6 flex items-center justify-between border-b border-hairline bg-[#0e131f] flex-shrink-0">
        <div className="flex items-center gap-3">
          <i className="fa-regular fa-folder-open text-indigo-400 text-sm"></i>
          <div>
            <h2 className="text-xs font-semibold text-slate-200">Knowledge Base Index</h2>
            <p className="text-[10px] text-slate-500 font-mono">Pinecone Vector Database (rag-bot)</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files?.[0]) {
                onUploadFile(e.target.files[0]);
                e.target.value = '';
              }
            }}
            accept=".pdf,.txt,.docx"
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadProgress !== null}
            className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:bg-[#161f30] text-white font-medium text-xs transition-fast flex items-center gap-1.5 shadow-sm"
          >
            <i className="fa-solid fa-cloud-arrow-up text-[10px]"></i>
            <span>Upload Document</span>
          </button>
        </div>
      </header>

      {/* 2. Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5 max-w-4xl mx-auto w-full">
        {/* Upload Zone & Drag and Drop */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`p-6 rounded-xl border border-dashed transition-fast text-center cursor-pointer ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-950/20'
              : 'border-hairline hover:border-slate-600 bg-[#0e131f]'
          }`}
        >
          <div className="h-9 w-9 rounded-lg bg-[#161f30] border border-hairline flex items-center justify-center text-indigo-400 mx-auto mb-2.5">
            <i className="fa-solid fa-cloud-arrow-up text-sm"></i>
          </div>
          <p className="text-xs font-medium text-slate-200 mb-0.5">
            Drag & drop PDF files here, or <span className="text-indigo-400 underline">browse</span>
          </p>
          <p className="text-[11px] text-slate-500">
            Parses via Docling, chunks with recursive token bounds, and vectors to Pinecone.
          </p>
        </div>

        {/* Upload Progress Notification */}
        {uploadProgress && (
          <div className="p-3.5 rounded-lg bg-[#0e131f] border border-indigo-500/30 text-xs space-y-2 animate-fadeIn">
            <div className="flex items-center justify-between">
              <span className="font-mono text-slate-300 truncate max-w-md">
                {uploadProgress.filename}
              </span>
              <span className="font-mono text-indigo-400 font-semibold text-[11px]">
                {uploadProgress.status}
              </span>
            </div>
            <div className="h-1.5 w-full bg-[#161f30] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 transition-all duration-300"
                style={{ width: `${uploadProgress.progress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Documents Table Header & Filter */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-300">Indexed Files</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#161f30] border border-hairline text-slate-400">
                {documents.length}
              </span>
            </div>

            <div className="w-56">
              <input
                type="text"
                placeholder="Search indexed files..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full bg-[#0e131f] border border-hairline rounded px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl border border-hairline bg-[#0e131f] overflow-hidden">
            {filteredDocs.length === 0 ? (
              <div className="p-10 text-center text-slate-500 text-xs">
                <i className="fa-regular fa-folder-open text-2xl mb-2 block opacity-30"></i>
                No documents found matching the filter.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-[#090d16] border-b border-hairline text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-2.5">Document</th>
                    <th className="px-4 py-2.5">Size</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5 text-right">Inquire</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline">
                  {filteredDocs.map((doc, idx) => (
                    <tr key={idx} className="hover:bg-[#161f30]/40 transition-fast">
                      <td className="px-4 py-3 font-medium text-slate-200 flex items-center gap-2">
                        <i className="fa-regular fa-file-pdf text-rose-400 text-xs"></i>
                        <span className="truncate max-w-xs">{doc.filename}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                        {doc.size_bytes ? `${Math.round(doc.size_bytes / 1024)} KB` : 'N/A'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                          <span className="h-1 w-1 rounded-full bg-emerald-400"></span>
                          Indexed
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => onAskAboutDoc(`Please summarize the core findings of ${doc.filename}.`)}
                          className="text-indigo-400 hover:text-indigo-300 font-medium text-[11px] transition-fast inline-flex items-center gap-1"
                        >
                          <span>Query</span>
                          <i className="fa-solid fa-arrow-right text-[9px]"></i>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
