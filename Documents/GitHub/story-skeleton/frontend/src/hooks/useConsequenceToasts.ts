import { useState, useEffect, useCallback, useRef } from 'react';
import { type ConsequenceToast } from '../components/ConsequenceToaster';
import { useSettings } from '../contexts/SettingsContext';

interface ConsequenceToastEvent {
  type: 'consequence_toast';
  payload: {
    kind: ConsequenceToast['kind'];
    label: string;
    delta?: number;
    npc_id?: string;
  };
}

export const useConsequenceToasts = () => {
  const { settings } = useSettings();
  const [toasts, setToasts] = useState<ConsequenceToast[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const addToast = useCallback((toast: Omit<ConsequenceToast, 'id' | 'timestamp'>) => {
    // Check if toasts are enabled
    if (!settings.toastsEnabled) {
      return;
    }

    // Check severity filter
    const isImportant = ['promise_breached', 'promise_fulfilled'].includes(toast.kind);
    if (settings.toastsMinSeverity === 'important' && !isImportant) {
      return;
    }

    const newToast: ConsequenceToast = {
      ...toast,
      id: `${toast.kind}-${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
    };
    
    setToasts(prev => [...prev, newToast]);
    
    // Auto-dismiss after 2.5 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== newToast.id));
    }, 2500);
  }, [settings.toastsEnabled, settings.toastsMinSeverity]);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const connectWebSocket = useCallback(() => {
    // Don't connect if toasts are disabled
    if (!settings.toastsEnabled) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected for consequence toasts');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data: ConsequenceToastEvent = JSON.parse(event.data);
        if (data.type === 'consequence_toast') {
          addToast(data.payload);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      
      // Attempt to reconnect after 3 seconds
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
  }, [addToast]);

  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    connectWebSocket();
    
    return () => {
      disconnectWebSocket();
    };
  }, [connectWebSocket, disconnectWebSocket, settings.toastsEnabled]);

  return {
    toasts,
    isConnected,
    dismissToast,
    addToast, // For testing purposes
  };
};
