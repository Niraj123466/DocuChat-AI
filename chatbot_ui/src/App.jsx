import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { useDocuChatApi } from './hooks/useDocuChatApi';
import { Sidebar } from './components/Sidebar';
import { ChatView } from './components/Chat/ChatView';
import { DocumentView } from './components/Documents/DocumentView';
import { IntelligenceView } from './components/Intelligence/IntelligenceView';
import { SourceDrawer } from './components/Sources/SourceDrawer';
import { CommandPalette } from './components/CommandPalette';
import { StatusBar } from './components/StatusBar';
import { AuthModal } from './components/Auth/AuthModal';

export default function App() {
  const { user, isAuthenticated, isAuthModalOpen, setIsAuthModalOpen, logout } = useAuth();

  const {
    conversations,
    activeConvId,
    messages,
    documents,
    activeTab,
    selectedCitation,
    apiOnline,
    serviceStatus,
    isLoading,
    loadingStep,
    errorBanner,
    uploadProgress,
    telemetryData,
    setActiveTab,
    setSelectedCitation,
    setErrorBanner,
    selectConversation,
    startNewConversation,
    deleteConversation,
    sendMessage,
    uploadDocument,
  } = useDocuChatApi();

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Global Keyboard Shortcuts (⌘K, ⌘B, ⌘N)
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;

      if (isCmdOrCtrl && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      } else if (isCmdOrCtrl && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        setIsSidebarCollapsed((prev) => !prev);
      } else if (isCmdOrCtrl && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        startNewConversation();
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [startNewConversation]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#090d16] font-sans text-slate-100 select-none">
      {/* Main Horizontal Workbench: Sidebar + Primary Worksurface + Source Drawer */}
      <div className="flex flex-1 overflow-hidden">
        {/* 1. Left Nav & Tree */}
        <Sidebar
          conversations={conversations}
          activeConvId={activeConvId}
          activeTab={activeTab}
          documentsCount={documents.length}
          apiOnline={apiOnline}
          user={user}
          isAuthenticated={isAuthenticated}
          onLogout={logout}
          onOpenAuthModal={() => setIsAuthModalOpen(true)}
          onSelectConversation={selectConversation}
          onNewConversation={startNewConversation}
          onDeleteConversation={deleteConversation}
          onSelectTab={setActiveTab}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        />

        {/* 2. Center Primary Worksurface Canvas */}
        <main className="flex-1 flex flex-col h-full overflow-hidden min-w-0 bg-[#090d16]">
          {activeTab === 'chat' && (
            <ChatView
              messages={messages}
              activeConvId={activeConvId}
              conversations={conversations}
              isLoading={isLoading}
              loadingStep={loadingStep}
              errorBanner={errorBanner}
              onDismissError={() => setErrorBanner(null)}
              onSendMessage={sendMessage}
              onUploadFile={uploadDocument}
              onSelectCitation={setSelectedCitation}
              activeDocumentCount={documents.length}
              onNewConversation={startNewConversation}
            />
          )}

          {activeTab === 'documents' && (
            <DocumentView
              documents={documents}
              onUploadFile={uploadDocument}
              uploadProgress={uploadProgress}
              onAskAboutDoc={(query) => {
                setActiveTab('chat');
                sendMessage(query);
              }}
            />
          )}

          {activeTab === 'intelligence' && (
            <IntelligenceView
              telemetryData={telemetryData}
              serviceStatus={serviceStatus}
            />
          )}
        </main>

        {/* 3. Right Slide-out Source Inspector Drawer */}
        {selectedCitation && (
          <SourceDrawer
            citation={selectedCitation}
            onClose={() => setSelectedCitation(null)}
            onAskAboutSource={(query) => {
              setSelectedCitation(null);
              setActiveTab('chat');
              sendMessage(query);
            }}
          />
        )}
      </div>

      {/* 4. Bottom Fixed Telemetry Instrument Bar */}
      <StatusBar
        apiOnline={apiOnline}
        telemetryData={telemetryData}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      {/* 5. Command Palette (⌘K) Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        conversations={conversations}
        onSelectConversation={selectConversation}
        onNewConversation={startNewConversation}
        onSelectTab={setActiveTab}
        onTriggerUpload={() => {
          setActiveTab('documents');
        }}
      />

      {/* 6. Auth Modal (Login / Register) */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
}
