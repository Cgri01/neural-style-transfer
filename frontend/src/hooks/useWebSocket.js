import { useState, useRef, useCallback, useEffect } from "react";

const useWebSocket = (url, onMessage, onOpen, onClose, onError) => {
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState(null);
    const wsRef = useRef(null);
    const urlRef = useRef(url);
    const reconnectTimeoutRef = useRef(null);
    const reconnectAttempts = useRef(0);
    const maxReconnectAttempts = 5;

    const onMessageRef = useRef(onMessage);
    const onOpenRef = useRef(onOpen);
    const onCloseRef = useRef(onClose);
    const onErrorRef = useRef(onError);

    useEffect(() => {
        onMessageRef.current = onMessage;
        onOpenRef.current = onOpen;
        onCloseRef.current = onClose;
        onErrorRef.current = onError;
    }, [onMessage, onOpen, onClose, onError]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        if (wsRef.current) {
            if (
                wsRef.current.readyState === WebSocket.OPEN ||
                wsRef.current.readyState === WebSocket.CONNECTING
            ) {
                wsRef.current.close();
            }
            wsRef.current = null;
        }

        setIsConnected(false);
    }, []);

    const connect = useCallback(() => {
        // URL degisti (ornegin process_size) -> eski baglantiyi kapat, yenisini ac
        if (urlRef.current !== url && wsRef.current) {
            disconnect();
        }
        urlRef.current = url;

        if (
            wsRef.current &&
            (wsRef.current.readyState === WebSocket.OPEN ||
                wsRef.current.readyState === WebSocket.CONNECTING)
        ) {
            return;
        }

        try {
            console.log(`Websocket connecting: ${url}`);
            const ws = new WebSocket(url);
            ws.binaryType = "arraybuffer";
            wsRef.current = ws;

            ws.onopen = () => {
                console.log("Websocket connected");
                setIsConnected(true);
                setConnectionError(null);
                reconnectAttempts.current = 0;
                if (onOpenRef.current) onOpenRef.current();
            };

            ws.onmessage = (event) => {
                if (onMessageRef.current && event.data) {
                    const blob = new Blob([event.data], { type: "image/jpeg" });
                    onMessageRef.current(blob);
                }
            };

            ws.onclose = (event) => {
                console.log(`Websocket disconnected: ${event.code} - ${event.reason}`);
                setIsConnected(false);

                if (onCloseRef.current) onCloseRef.current(event);

                if (reconnectTimeoutRef.current) {
                    clearTimeout(reconnectTimeoutRef.current);
                }

                if (reconnectAttempts.current < maxReconnectAttempts) {
                    reconnectTimeoutRef.current = setTimeout(() => {
                        reconnectAttempts.current++;
                        connect();
                    }, 2000);
                }
            };

            ws.onerror = (error) => {
                console.log("Websocket error", error);
                setConnectionError("Websocket connection error");
                if (onErrorRef.current) onErrorRef.current(error);
            };
        } catch (error) {
            console.error("Websocket creating error:", error);
            setConnectionError(error.message);
        }
    }, [url, disconnect]);

    const send = useCallback((data) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(data);
            return true;
        }
        return false;
    }, []);

    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    const isReady = isConnected && wsRef.current?.readyState === WebSocket.OPEN;

    return {
        isConnected: isReady,
        connectionError,
        connect,
        disconnect,
        send,
    };
};

export default useWebSocket;
