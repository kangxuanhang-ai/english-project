export const report = async (url: string, body: any) => {
    const blob = new Blob([JSON.stringify(body)], { type: 'application/json' })
    navigator.sendBeacon(url, blob)
}


export const reportFetch = async (url: string, body: any) => {
    const response = await fetch(url, {
        method: 'POST',
        body: JSON.stringify(body),
        keepalive: true,
        headers: {
            'Content-Type': 'application/json'
        }
    })
    return response.json()
}