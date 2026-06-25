import type { PvDto,TrackerConfig } from '@en/common/tracker';
import { report } from '@/report';
const reportView = (visitorId: string,config: TrackerConfig) => {
    let url = config.baseUrl + config.pv.api
    const isHash = window.location.href.includes('#') //如果携带了# 说明是hash模式
    const body: PvDto = {
        visitorId,
        url: window.location.protocol + '//' + window.location.host,
        referrer: document.referrer,
        path: isHash ? '/' + window.location.hash : window.location.pathname,
    }
    report(url, body)
}

export const reportPv = (visitorId: string,config: TrackerConfig) => {
    reportView(visitorId,config) //初始化上报
    //路由的模式 hash history
    window.addEventListener('hashchange', (e) => {
        reportView(visitorId,config)
    })
   //popstate 前进和后退
   //router.push router.replace
    window.addEventListener('popstate', (e) => {
        reportView(visitorId,config)
    })
    const originalPushState = history.pushState //获取原始的pushState方法
    history.pushState = function () {
        originalPushState.apply(this, arguments)
        reportView(visitorId,config)
    }
    const originalReplaceState = history.replaceState //获取原始的replaceState方法
    history.replaceState = function () {
        originalReplaceState.apply(this, arguments)
        reportView(visitorId,config)
    }
}