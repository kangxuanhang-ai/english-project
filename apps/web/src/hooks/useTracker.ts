import { Tracker } from '@en/tracker'

const tracker = new Tracker({
    baseUrl: '/api/v1',
    uv: {
        api: '/tracker/uv',
        updateApi: '/tracker/update-uv',
    },
    pv: {
        api: '/tracker/pv',
    },
    event: {
        api: '/tracker/event',
    },
    error: {
        api: '/tracker/error',
    },
    performance: {
        api: '/tracker/performance',
    },
})

export function useTracker() {
    return tracker
}
