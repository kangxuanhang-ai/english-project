import type { TrackerConfig } from '@en/common/tracker';
import { getFingerprint } from '@/uv';
import { reportEvent } from '@/event';
import { reportError } from '@/error';
import { reportPv } from '@/pv';
import { reportPerformance } from '@/performance';
import { reportFetch } from '@/report';
export class Tracker {
    private config: TrackerConfig
    private visitorId: string | null = null
    private initPromise: Promise<void> | null = null
    constructor(config: TrackerConfig) {
        this.config = config
        this.init() //初始化方法
    }
    //protected 允许子类和内部使用
    protected async init() {
        if (this.initPromise) return this.initPromise //确保他是同一个promise
        //IIFE立即执行函数
        this.initPromise = (async () => {
            let config = this.config
            this.visitorId = await getFingerprint(config)
            reportEvent(this.visitorId, config) //事件上报目前没有visitorId先随便写一个
            reportError(this.visitorId, config) //错误上报目前没有visitorId先随便写一个
            reportPv(this.visitorId, config) //页面上报目前没有visitorId先随便写一个
            reportPerformance(this.visitorId, config) //性能上报目前没有visitorId先随便写一个
        })()
        return this.initPromise
    }

    public async setUserId(userId: string) {
        await this.init()
        let url = this.config.baseUrl + this.config.uv.updateApi
        await reportFetch(url, {
            visitorId: this.visitorId,
            userId: userId
        })
    }

    /** 上报自定义事件（看板统计用） */
    public async trackEvent(type: string, payload?: Record<string, unknown>) {
        await this.init()
        if (!this.visitorId) return
        const url = this.config.baseUrl + this.config.event.api
        await reportFetch(url, {
            visitorId: this.visitorId,
            event: type,
            payload: payload ?? {},
            url: typeof window !== 'undefined' ? window.location.href : '',
        })
    }
}
