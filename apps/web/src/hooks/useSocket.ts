import { io, type Socket } from 'socket.io-client';
import { socketUrl } from '@/apis';
import { useUserStore } from '@/stores/user';
let socket: Socket | null = null;
export const useSocket = () => {
    const userStore = useUserStore();
    //连接socket
    const connect = () => {
        const token = userStore.getAccessToken;
        if (!token) return; //如果没有token不可以连接
        if (socket) return; //如果已经连接了就不要在重复连接了
        socket = io(socketUrl, {
            transports: ['websocket'],
            autoConnect: true, //是否自动连接
            reconnection: true, //是否自动重连
            reconnectionAttempts: 5, //重连次数
            reconnectionDelay: 1000, //重连时间
            reconnectionDelayMax: 5000, //最大重连时间
            timeout: 20000, //超时时间
            query: {
                token
            }
        })
        //为了threeShaking
        if(import.meta.hot){
            import.meta.hot.data.socket = socket;
        }
    }

    //断开socket
    const disconnect = () => {
      if(socket){
        socket.disconnect(); //断开连接
        socket.removeAllListeners(); //移除所有事件监听
        socket = null; //清空socket
        if(import.meta.hot){
            import.meta.hot.data.socket = null;
        }
      }
    }
    //获取socket
    const getSocket = (): Socket | null => {
        if(socket){
            return socket;
        }
        if(import.meta.hot){
            return import.meta.hot.data.socket;
        }
        return null;
    }

    return {
        connect,
        disconnect,
        getSocket
    }
}