import { io, type Socket } from 'socket.io-client';
import { socketUrl } from '@/apis';
import { ensureValidToken } from '@/apis/auth';
import { useUserStore } from '@/stores/user';

let socket: Socket | null = null;

export const useSocket = () => {
    const userStore = useUserStore();

    const connect = async () => {
        const token = await ensureValidToken();
        if (!token) return;

        if (socket?.connected) {
            if (socket.io.opts.query?.token !== token) {
                disconnect();
            } else {
                return;
            }
        }

        socket = io(socketUrl || undefined, {
            transports: ['websocket'],
            autoConnect: true,
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            query: {
                token,
            },
        });

        if (import.meta.hot) {
            import.meta.hot.data.socket = socket;
        }
    };

    const disconnect = () => {
        if (socket) {
            socket.disconnect();
            socket.removeAllListeners();
            socket = null;
            if (import.meta.hot) {
                import.meta.hot.data.socket = null;
            }
        }
    };

    const getSocket = (): Socket | null => {
        if (socket) {
            return socket;
        }
        if (import.meta.hot) {
            return import.meta.hot.data.socket;
        }
        return null;
    };

    return {
        connect,
        disconnect,
        getSocket,
    };
};
