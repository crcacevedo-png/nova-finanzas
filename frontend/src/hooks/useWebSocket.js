// /app/frontend/src/hooks/useWebSocket.js
// Hook personalizado para conexiones WebSocket en tiempo real

import { useState, useEffect, useCallback, useRef } from 'react';

const WS_RECONNECT_INTERVAL = 3000; // 3 segundos
const WS_MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Hook para gestionar conexiones WebSocket
 * @param {string} channel - Canal a conectar ('caja', 'agenda', 'pos')
 * @param {Object} options - Opciones de configuración
 * @returns {Object} Estado y funciones del WebSocket
 */
export function useWebSocket(channel, options = {}) {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoConnect = true,
    enabled = true
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const isConnecting = useRef(false);
  
  // Usar refs para los callbacks para evitar re-renders infinitos
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);
  
  // Actualizar refs cuando cambien los callbacks
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  
  useEffect(() => {
    onConnectRef.current = onConnect;
  }, [onConnect]);
  
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);
  
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  // Construir URL del WebSocket
  const getWebSocketUrl = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) return null;

    // Usar la misma base URL que el API pero con protocolo ws/wss
    const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = baseUrl.replace(/^https?:\/\//, '').replace(/\/api$/, '');
    
    return `${wsProtocol}://${wsHost}/ws/${channel}?token=${token}`;
  }, [channel]);

  // Conectar al WebSocket
  const connect = useCallback(() => {
    if (!enabled || isConnecting.current) return;
    
    const url = getWebSocketUrl();
    if (!url) {
      console.warn('No se puede conectar WebSocket: token no disponible');
      return;
    }

    // Cerrar conexión existente
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
    }

    isConnecting.current = true;
    setConnectionStatus('connecting');
    
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`✅ WebSocket conectado al canal: ${channel}`);
        isConnecting.current = false;
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        
        // Configurar ping interval para mantener conexión viva
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000); // Ping cada 25 segundos
        
        if (onConnectRef.current) onConnectRef.current();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Ignorar pings/pongs
          if (data.type === 'ping' || data.type === 'pong') {
            return;
          }
          
          setLastMessage(data);
          if (onMessageRef.current) onMessageRef.current(data);
        } catch (e) {
          console.error('Error parseando mensaje WebSocket:', e);
        }
      };

      ws.onclose = (event) => {
        console.log(`WebSocket desconectado del canal: ${channel}`, event.code);
        isConnecting.current = false;
        setIsConnected(false);
        setConnectionStatus('disconnected');
        wsRef.current = null;
        
        // Limpiar ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        if (onDisconnectRef.current) onDisconnectRef.current();
        
        // Intentar reconectar si no fue un cierre intencional y está habilitado
        // Código 1000 = cierre normal, 4001 = no autorizado
        if (event.code !== 1000 && event.code !== 4001 && enabled && reconnectAttempts.current < WS_MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          setConnectionStatus('reconnecting');
          console.log(`Intentando reconectar (${reconnectAttempts.current}/${WS_MAX_RECONNECT_ATTEMPTS})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, WS_RECONNECT_INTERVAL);
        } else if (reconnectAttempts.current >= WS_MAX_RECONNECT_ATTEMPTS) {
          console.warn(`Máximo de intentos de reconexión alcanzado para canal: ${channel}`);
          setConnectionStatus('failed');
        }
      };

      ws.onerror = (error) => {
        console.error('Error en WebSocket:', error);
        isConnecting.current = false;
        setConnectionStatus('error');
        if (onErrorRef.current) onErrorRef.current(error);
      };

    } catch (error) {
      console.error('Error creando WebSocket:', error);
      isConnecting.current = false;
      setConnectionStatus('error');
      if (onErrorRef.current) onErrorRef.current(error);
    }
  }, [channel, enabled, getWebSocketUrl]);

  // Desconectar
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Desconexión manual');
      wsRef.current = null;
    }
    
    isConnecting.current = false;
    reconnectAttempts.current = 0;
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  // Enviar mensaje
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // Efecto para conectar automáticamente
  useEffect(() => {
    if (autoConnect && enabled) {
      // Pequeño delay para evitar conexiones durante renders iniciales
      const timeoutId = setTimeout(() => {
        connect();
      }, 100);
      
      return () => {
        clearTimeout(timeoutId);
        disconnect();
      };
    }
    
    return () => {
      disconnect();
    };
  }, [autoConnect, enabled, channel]); // Solo dependencias estables

  return {
    isConnected,
    connectionStatus,
    lastMessage,
    connect,
    disconnect,
    sendMessage
  };
}

/**
 * Hook específico para el canal de Caja
 */
export function useCajaWebSocket(options = {}) {
  return useWebSocket('caja', options);
}

/**
 * Hook específico para el canal de Agenda
 */
export function useAgendaWebSocket(options = {}) {
  return useWebSocket('agenda', options);
}

/**
 * Hook específico para el canal de POS
 */
export function usePOSWebSocket(options = {}) {
  return useWebSocket('pos', options);
}

export default useWebSocket;
