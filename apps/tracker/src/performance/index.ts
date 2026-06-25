import type { PerformanceDto,TrackerConfig } from '@en/common/tracker';
import { report } from '@/report';
import { onINP, onCLS } from 'web-vitals'
export const reportPerformance = async (visitorId: string,config: TrackerConfig) => {
    let url = config.baseUrl + config.performance.api
    let fp = 0 //FP 首次绘制时间
    let fcp = 0 //FCP 首次内容绘制时间
    let lcp = 0 //LCP 最大内容绘制时间
    let inp = 0 //INP 交互性能指标
    let cls = 0 //CLS 累积布局偏移
    //FP 和 FCP
    let performanceEntries = performance.getEntriesByType("paint");
    const fpEntry = performanceEntries.find(entry => entry.name === "first-paint");
    const fcpEntry = performanceEntries.find(entry => entry.name === "first-contentful-paint");
    if (fpEntry) {
        fp = fpEntry.startTime;
    }
    if (fcpEntry) {
        fcp = fcpEntry.startTime;
    }
    let lcpPromise = new Promise<{ lcpTime: number, lcpObsercer: PerformanceObserver }>((resolve) => {
        let lcpObsercer = new PerformanceObserver((entryList) => {
            resolve({
                lcpTime: entryList.getEntries().at(-1)?.startTime || 0,
                lcpObsercer
            });
        })
        lcpObsercer.observe({ type: 'largest-contentful-paint', buffered: true }); //buffered 历史记录和新的LCP性能都监听
    })
    const { lcpTime, lcpObsercer } = await lcpPromise;
    lcpObsercer.disconnect(); //断开
    lcp = lcpTime;
    //INP
    onINP((metric) => {
        inp = metric.value;
    });
    //CLS
    onCLS((metric) => {
        cls = metric.value;
    });
    window.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            const body: PerformanceDto = {
                visitorId,
                fp,
                fcp,
                lcp,
                inp,
                cls
            }
            report(url, body)
        }
    }, { once: true })
}