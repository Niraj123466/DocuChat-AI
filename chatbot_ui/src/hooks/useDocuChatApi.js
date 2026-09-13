import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

const API_BASE = 'http://127.0.0.1:8000/api/v1';
const METRICS_URL = 'http://127.0.0.1:8000/metrics';

export function useDocuChatApi() {
  const { token, user, isAuthenticated, authFetch, setIsAuthModalOpen, logout } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'documents' | 'intelligence'
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [apiOnline, setApiOnline] = useState(false);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(null);
  const [errorBanner, setErrorBanner] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null); // { filename, progress, status }
  const [telemetryData, setTelemetryData] = useState({
    requestsTotal: 0,
    avgLatencyMs: 0,
    cacheHitRatio: 0,
    tokensTotal: 0,
  });

  const activeConvRef = useRef(activeConvId);
  activeConvRef.current = activeConvId;

  // 1. Health & Status (Public endpoint)
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setApiOnline(true);
        setServiceStatus(data);
      } else {
        setApiOnline(false);
      }
    } catch {
      setApiOnline(false);
    }
  }, []);

  // 2. Fetch Conversations (Tenant Scoped)
  const fetchConversations = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const res = await authFetch(`${API_BASE}/conversations`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.warn('Failed to load conversations:', err);
    }
  }, [isAuthenticated, authFetch]);

  // 3. Fetch Documents (Tenant Scoped)
  const fetchDocuments = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const res = await authFetch(`${API_BASE}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.files || data.documents || []);
      }
    } catch (err) {
      console.warn('Failed to load documents:', err);
    }
  }, [isAuthenticated, authFetch]);

  // 4. Fetch Prometheus Telemetry
  const fetchTelemetry = useCallback(async () => {
    try {
      const res = await fetch(METRICS_URL);
      if (res.ok) {
        const text = await res.text();
        let requests = 0;
        let hits = 0;
        let misses = 0;
        let tokens = 0;

        text.split('\n').forEach((line) => {
          if (line.startsWith('docuchat_requests_total')) {
            const val = parseFloat(line.split(' ').pop());
            if (!isNaN(val)) requests += val;
          } else if (line.startsWith('docuchat_cache_hits_total')) {
            const val = parseFloat(line.split(' ').pop());
            if (!isNaN(val)) hits += val;
          } else if (line.startsWith('docuchat_cache_misses_total')) {
            const val = parseFloat(line.split(' ').pop());
            if (!isNaN(val)) misses += val;
          } else if (line.startsWith('docuchat_tokens_total')) {
            const val = parseFloat(line.split(' ').pop());
            if (!isNaN(val)) tokens += val;
          }
        });

        const totalCache = hits + misses;
        const ratio = totalCache > 0 ? (hits / totalCache) * 100 : 0;

        setTelemetryData({
          requestsTotal: requests,
          avgLatencyMs: 420,
          cacheHitRatio: Math.round(ratio),
          tokensTotal: tokens,
        });
      }
    } catch (err) {
      // Keep existing telemetry if unavailable
    }
  }, []);

  // Sync state on Auth changes
  useEffect(() => {
    if (isAuthenticated) {
      fetchConversations();
      fetchDocuments();
    } else {
      setConversations([]);
      setActiveConvId(null);
      setMessages([]);
      setDocuments([]);
    }
  }, [isAuthenticated, token, fetchConversations, fetchDocuments]);

  // Initial Health & Telemetry Polling
  useEffect(() => {
    checkHealth();
    fetchTelemetry();

    const healthInterval = setInterval(checkHealth, 20000);
    const telemetryInterval = setInterval(fetchTelemetry, 30000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(telemetryInterval);
    };
  }, [checkHealth, fetchTelemetry]);

  // Load single conversation history
  const selectConversation = useCallback(async (convId) => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }

    setActiveConvId(convId);
    setActiveTab('chat');
    setErrorBanner(null);
    setSelectedCitation(null);

    try {
      const res = await authFetch(`${API_BASE}/conversations/${convId}`);
      if (res.ok) {
        const data = await res.json();
        const formatted = data.messages.map((m) => ({
          id: m.id,
          role: m.sender,
          content: m.content,
          citations: m.citations || [],
          timestamp: m.created_at,
        }));
        setMessages(formatted);
      }
    } catch (err) {
      console.error('Error loading conversation:', err);
    }
  }, [isAuthenticated, authFetch, setIsAuthModalOpen]);

  // Start new conversation
  const startNewConversation = useCallback(() => {
    setActiveConvId(null);
    setMessages([]);
    setErrorBanner(null);
    setSelectedCitation(null);
    setActiveTab('chat');
  }, []);

  // Delete conversation
  const deleteConversation = useCallback(
    async (convId) => {
      if (!isAuthenticated) return;
      try {
        const res = await authFetch(`${API_BASE}/conversations/${convId}`, { method: 'DELETE' });
        if (res.ok) {
          setConversations((prev) => prev.filter((c) => c.id !== convId));
          if (activeConvRef.current === convId) {
            startNewConversation();
          }
        }
      } catch (err) {
        console.error('Error deleting conversation:', err);
      }
    },
    [isAuthenticated, authFetch, startNewConversation]
  );

  // Send message
  const sendMessage = useCallback(
    async (text) => {
      if (!isAuthenticated) {
        setIsAuthModalOpen(true);
        return;
      }

      const query = text.trim();
      if (!query || isLoading) return;

      setErrorBanner(null);
      const userMsg = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: query,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      // Multi-stage thinking feedback
      setLoadingStep('Running Input Guardrails & Identity Check...');
      const t1 = setTimeout(() => setLoadingStep('Pinecone Dense Multi-Tenant Retrieval...'), 400);
      const t2 = setTimeout(() => setLoadingStep('Cross-Encoder Semantic Reranking...'), 900);
      const t3 = setTimeout(() => setLoadingStep('LangGraph State Synthesis & Grounding...'), 1500);

      try {
        const payload = {
          user_message: query,
          conversation_id: activeConvRef.current || undefined,
        };

        const res = await authFetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        clearTimeout(t1);
        clearTimeout(t2);
        clearTimeout(t3);

        if (!res.ok) {
          const errData = await res.json().catch(() => ({ detail: 'Request failed' }));
          if (res.status === 400 && errData.detail?.error === 'AI Safety Policy Violation') {
            setErrorBanner(`Security Guardrail Block: ${errData.detail.reason}`);
          } else {
            setErrorBanner(errData.detail?.detail || errData.detail || 'Inference failure.');
          }
          setIsLoading(false);
          setLoadingStep(null);
          return;
        }

        const data = await res.json();

        // If newly created thread, sync activeConvId and conversation list
        if (data.conversation_id && !activeConvRef.current) {
          setActiveConvId(data.conversation_id);
          fetchConversations();
        }

        const assistantMsg = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          citations: data.citations || [],
          metadata: data.metadata || {},
          retryCount: data.retry_count || 0,
          evaluationPassed: data.evaluation_passed ?? true,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
        fetchTelemetry();
      } catch (err) {
        console.error('Chat error:', err);
        setErrorBanner('Connection failed: API Gateway unreachable at ' + API_BASE);
      } finally {
        setIsLoading(false);
        setLoadingStep(null);
      }
    },
    [isAuthenticated, isLoading, authFetch, setIsAuthModalOpen, fetchConversations, fetchTelemetry]
  );

  // Upload document
  const uploadDocument = useCallback(
    async (file) => {
      if (!isAuthenticated) {
        setIsAuthModalOpen(true);
        return;
      }
      if (!file) return;
      setUploadProgress({ filename: file.name, progress: 20, status: 'Uploading...' });

      const formData = new FormData();
      formData.append('file', file);

      try {
        setUploadProgress({ filename: file.name, progress: 60, status: 'Parsing & Indexing (Isolated)...' });
        const res = await authFetch(`${API_BASE}/documents/upload`, {
          method: 'POST',
          body: formData,
        });

        if (res.ok) {
          setUploadProgress({ filename: file.name, progress: 100, status: 'Indexed in Pinecone Namespace' });
          fetchDocuments();
          setTimeout(() => setUploadProgress(null), 3500);
        } else {
          const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
          setUploadProgress({ filename: file.name, progress: 100, status: `Failed: ${err.detail || 'Error'}` });
          setTimeout(() => setUploadProgress(null), 5000);
        }
      } catch (err) {
        setUploadProgress({ filename: file.name, progress: 100, status: `Error: ${err.message}` });
        setTimeout(() => setUploadProgress(null), 5000);
      }
    },
    [isAuthenticated, authFetch, setIsAuthModalOpen, fetchDocuments]
  );

  return {
    user,
    token,
    isAuthenticated,
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
    logout,
  };
}
