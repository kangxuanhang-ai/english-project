import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)

const CN_TZ = 'Asia/Shanghai'

/** 后端 naive ISO 为 UTC，展示为北京时间 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const hasTz = /[zZ]|[+-]\d{2}:\d{2}$/.test(value)
  const d = hasTz ? dayjs(value) : dayjs.utc(value)
  return d.tz(CN_TZ).format('YYYY/M/D HH:mm:ss')
}
