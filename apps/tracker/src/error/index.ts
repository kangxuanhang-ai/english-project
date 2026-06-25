import type { ErrorDto, TrackerConfig } from '@en/common/tracker';
import { report } from '@/report';
export const reportError = (visitorId: string,config: TrackerConfig) => {
    //捕获全局js错误
    let url = config.baseUrl + config.error.api
    window.addEventListener('error', (e: ErrorEvent) => {
       const body:ErrorDto = {
          visitorId,
          error:'js', //js错误
          message:e.message, //错误信息
          stack:e.error.stack, //错误堆栈
          url:e.filename, //错误文件
       }
       report(url, body)
    })
    //捕获全局Promise错误
    window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
        const isError = e.reason instanceof Error
        const body:ErrorDto = {
            visitorId,
            error:'promise', //promise错误
            message:isError ? e.reason.message : JSON.stringify(e.reason),
            stack:isError ? e.reason.stack : 'Promise Rejection',
            url:window.location.href,
        }
        report(url, body)
    })
}