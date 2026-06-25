<script setup lang="ts">
import { onMounted, onUnmounted, ref, shallowRef, nextTick, computed } from 'vue';
import type { ECharts } from 'echarts';
import type { DashboardStats, TrendPoint } from '@en/common/user';
import { getDashboard } from '@/apis/user';
import { exportPdf, exportPng } from '@/hooks/useDashboardExport';
import { ElMessage } from 'element-plus';

const loading = ref(true);
const loadError = ref(false);
const data = ref<DashboardStats | null>(null);
const wordChartRef = ref<HTMLDivElement | null>(null);
const pvChartRef = ref<HTMLDivElement | null>(null);
const dashboardRef = ref<HTMLDivElement | null>(null);
const wordChart = shallowRef<ECharts | null>(null);
const pvChart = shallowRef<ECharts | null>(null);
const exporting = ref(false);
let isAlive = true;

const statCards = computed(() => {
    if (!data.value) return [];
    const o = data.value.overview;
    return [
        { label: '累计打卡', value: o.checkInDays, suffix: '天', icon: '📌', tone: 'from-violet-500/10 to-indigo-500/5 ring-violet-200/60 text-violet-700' },
        { label: '掌握单词', value: o.masteredWords, suffix: '个', icon: '📚', tone: 'from-indigo-500/10 to-blue-500/5 ring-indigo-200/60 text-indigo-700' },
        { label: '已购课程', value: o.purchasedCourses, suffix: '门', icon: '🎓', tone: 'from-sky-500/10 to-cyan-500/5 ring-sky-200/60 text-sky-700' },
        { label: '近7日新掌握', value: o.wordsThisWeek, suffix: '个', icon: '✨', tone: 'from-emerald-500/10 to-teal-500/5 ring-emerald-200/60 text-emerald-700' },
    ];
});

const courseAccent = (index: number) => {
    const tones = [
        'bg-indigo-500',
        'bg-violet-500',
        'bg-sky-500',
        'bg-teal-500',
        'bg-amber-500',
        'bg-rose-500',
    ];
    return tones[index % tones.length];
};

/** 补齐近 7 天坐标，避免图表只有单点 */
function buildLast7DaysTrend(trend: TrendPoint[]) {
    const map = new Map<string, number>();
    for (const item of trend) {
        const key = item.date.slice(0, 10);
        map.set(key, item.count);
    }
    const labels: string[] = [];
    const values: number[] = [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(now.getDate() - i);
        const key = d.toISOString().slice(0, 10);
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        labels.push(`${mm}-${dd}`);
        values.push(map.get(key) ?? 0);
    }
    return { labels, values };
}

const chartTooltip = {
    trigger: 'axis' as const,
    backgroundColor: 'rgba(255,255,255,0.98)',
    borderColor: '#e4e4e7',
    borderWidth: 1,
    padding: [10, 14],
    textStyle: { color: '#52525b', fontSize: 12 },
    extraCssText: 'box-shadow: 0 12px 32px rgba(15,23,42,.08); border-radius: 12px;',
};

const renderCharts = async () => {
    if (!data.value || !isAlive) return;
    const echartsModule = await import('echarts');
    if (!isAlive) return;
    const echarts = echartsModule.default ?? echartsModule;

    const wordSeries = buildLast7DaysTrend(data.value.wordTrend);
    const pvSeries = buildLast7DaysTrend(data.value.activity.pvTrend);

    if (wordChartRef.value) {
        wordChart.value?.dispose();
        wordChart.value = echarts.init(wordChartRef.value, undefined, { renderer: 'canvas' });
        wordChart.value.setOption({
            tooltip: {
                ...chartTooltip,
                formatter: (params: unknown) => {
                    const p = (params as { name: string; value: number }[])[0];
                    return `<div style="font-weight:600;margin-bottom:4px">${p.name}</div>掌握 <b style="color:#6366f1">${p.value}</b> 个单词`;
                },
            },
            grid: { left: 8, right: 8, top: 12, bottom: 4, containLabel: true },
            xAxis: {
                type: 'category',
                data: wordSeries.labels,
                boundaryGap: false,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#a1a1aa', fontSize: 11, margin: 10 },
            },
            yAxis: {
                type: 'value',
                minInterval: 1,
                splitLine: { lineStyle: { color: '#f4f4f5', type: 'dashed' } },
                axisLabel: { color: '#a1a1aa', fontSize: 11 },
            },
            series: [{
                type: 'line',
                smooth: 0.35,
                symbol: 'circle',
                symbolSize: 7,
                showSymbol: wordSeries.values.some((v) => v > 0),
                data: wordSeries.values,
                lineStyle: { width: 3, color: '#6366f1' },
                itemStyle: { color: '#6366f1', borderColor: '#fff', borderWidth: 2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(99,102,241,0.28)' },
                        { offset: 1, color: 'rgba(99,102,241,0.02)' },
                    ]),
                },
            }],
        });
    }

    if (pvChartRef.value) {
        pvChart.value?.dispose();
        pvChart.value = echarts.init(pvChartRef.value, undefined, { renderer: 'canvas' });
        pvChart.value.setOption({
            tooltip: {
                ...chartTooltip,
                formatter: (params: unknown) => {
                    const p = (params as { name: string; value: number }[])[0];
                    return `<div style="font-weight:600;margin-bottom:4px">${p.name}</div>访问 <b style="color:#0d9488">${p.value}</b> 次`;
                },
            },
            grid: { left: 8, right: 8, top: 12, bottom: 4, containLabel: true },
            xAxis: {
                type: 'category',
                data: pvSeries.labels,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#a1a1aa', fontSize: 11, margin: 10 },
            },
            yAxis: {
                type: 'value',
                minInterval: 1,
                splitLine: { lineStyle: { color: '#f4f4f5', type: 'dashed' } },
                axisLabel: { color: '#a1a1aa', fontSize: 11 },
            },
            series: [{
                type: 'bar',
                barWidth: '42%',
                data: pvSeries.values,
                itemStyle: {
                    borderRadius: [8, 8, 2, 2],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#5eead4' },
                        { offset: 1, color: '#0d9488' },
                    ]),
                },
                emphasis: {
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#99f6e4' },
                            { offset: 1, color: '#14b8a6' },
                        ]),
                    },
                },
            }],
        });
    }
};

const onResize = () => {
    wordChart.value?.resize();
    pvChart.value?.resize();
};

onMounted(async () => {
    window.addEventListener('resize', onResize);
    await loadDashboard();
});

async function loadDashboard() {
    loading.value = true;
    loadError.value = false;
    try {
        const res = await getDashboard();
        if (res.code === 200) {
            data.value = res.data;
            loading.value = false;
            await nextTick();
            await renderCharts();
            return;
        }
        loadError.value = true;
    } catch {
        loadError.value = true;
        ElMessage.error('加载学习数据失败');
    } finally {
        loading.value = false;
    }
}

defineExpose({ reload: loadDashboard });

onUnmounted(() => {
    isAlive = false;
    window.removeEventListener('resize', onResize);
    wordChart.value?.dispose();
    pvChart.value?.dispose();
});

const handleExportPng = async () => {
    if (!dashboardRef.value) return;
    exporting.value = true;
    try {
        await exportPng(dashboardRef.value, `learning-report-${Date.now()}.png`);
    } catch {
        ElMessage.error('导出 PNG 失败');
    } finally {
        exporting.value = false;
    }
};

const handleExportPdf = async () => {
    if (!dashboardRef.value) return;
    exporting.value = true;
    try {
        await exportPdf(dashboardRef.value, `learning-report-${Date.now()}.pdf`);
    } catch {
        ElMessage.error('导出 PDF 失败');
    } finally {
        exporting.value = false;
    }
};
</script>

<template>
    <div
        id="learning-dashboard"
        ref="dashboardRef"
        class="dashboard-shell relative overflow-hidden rounded-3xl border border-indigo-100/80 bg-linear-to-br from-white via-indigo-50/30 to-violet-50/40 p-6 sm:p-8 shadow-[0_20px_60px_-24px_rgba(79,70,229,0.25)]"
    >
        <div class="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-indigo-200/30 blur-3xl" />
        <div class="pointer-events-none absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-teal-200/20 blur-3xl" />

        <div class="relative flex flex-wrap items-start justify-between gap-4 mb-8">
            <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-indigo-500/80 mb-1">Learning Insights</p>
                <h3 class="text-xl font-bold text-zinc-900 tracking-tight">我的学习数据</h3>
                <p class="text-xs text-zinc-500 mt-1">近 7 天学习趋势与课程掌握概览</p>
            </div>
            <div class="flex gap-2" data-export-hide>
                <button
                    type="button"
                    class="px-3.5 py-2 text-xs font-medium text-zinc-600 bg-white/80 border border-zinc-200/80 rounded-xl hover:bg-white hover:shadow-sm transition-all disabled:opacity-50"
                    :disabled="loading || exporting"
                    @click="handleExportPng"
                >
                    导出 PNG
                </button>
                <button
                    type="button"
                    class="px-3.5 py-2 text-xs font-medium text-white bg-linear-to-r from-indigo-600 to-violet-600 rounded-xl shadow-md shadow-indigo-500/20 hover:shadow-lg hover:shadow-indigo-500/25 transition-all disabled:opacity-50"
                    :disabled="loading || exporting"
                    @click="handleExportPdf"
                >
                    导出 PDF
                </button>
            </div>
        </div>

        <div v-if="loading" class="relative py-16 text-center">
            <div class="inline-flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100/80 mb-3">
                <span class="h-5 w-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
            </div>
            <p class="text-sm text-zinc-400">正在加载学习数据…</p>
        </div>

        <div v-else-if="loadError" class="relative py-16 text-center">
            <p class="text-sm text-zinc-500 mb-3">学习数据加载失败</p>
            <button
                type="button"
                class="text-sm text-indigo-600 hover:text-indigo-500 font-medium"
                @click="loadDashboard"
            >重试</button>
        </div>

        <div v-else-if="!data" class="relative py-16 text-center">
            <p class="text-sm text-zinc-400">暂无学习数据，开始学习后将在此展示统计</p>
        </div>

        <template v-else-if="data">
            <div class="relative grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
                <div
                    v-for="card in statCards"
                    :key="card.label"
                    class="stat-card group rounded-2xl bg-linear-to-br p-4 ring-1 ring-inset transition-transform hover:-translate-y-0.5"
                    :class="card.tone"
                >
                    <div class="flex items-start justify-between mb-3">
                        <span class="text-lg">{{ card.icon }}</span>
                        <span class="text-[10px] font-medium text-zinc-400 uppercase tracking-wide">{{ card.suffix }}</span>
                    </div>
                    <div class="text-3xl font-bold tabular-nums tracking-tight">{{ card.value }}</div>
                    <div class="text-xs text-zinc-500 mt-1">{{ card.label }}</div>
                </div>
            </div>

            <div class="relative grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
                <div class="chart-panel rounded-2xl bg-white/70 backdrop-blur-sm border border-white/80 p-4 sm:p-5 shadow-sm">
                    <div class="flex items-center justify-between mb-1">
                        <div>
                            <h4 class="text-sm font-semibold text-zinc-800">掌握单词趋势</h4>
                            <p class="text-[11px] text-zinc-400 mt-0.5">每日新掌握数量</p>
                        </div>
                        <span class="text-[10px] font-medium px-2 py-1 rounded-full bg-indigo-50 text-indigo-600">7 天</span>
                    </div>
                    <div ref="wordChartRef" class="h-56 sm:h-60 w-full" />
                </div>

                <div class="chart-panel rounded-2xl bg-white/70 backdrop-blur-sm border border-white/80 p-4 sm:p-5 shadow-sm">
                    <div class="flex items-center justify-between mb-1">
                        <div>
                            <h4 class="text-sm font-semibold text-zinc-800">学习活跃度</h4>
                            <p class="text-[11px] text-zinc-400 mt-0.5">页面访问次数</p>
                        </div>
                        <span class="text-[10px] font-medium px-2 py-1 rounded-full bg-teal-50 text-teal-600">7 天</span>
                    </div>
                    <div ref="pvChartRef" class="h-56 sm:h-60 w-full" />
                </div>
            </div>

            <div v-if="data.courseProgress.length" class="relative">
                <div class="flex items-end justify-between mb-4">
                    <div>
                        <h4 class="text-sm font-semibold text-zinc-800">课程进度</h4>
                        <p class="text-[11px] text-zinc-400 mt-0.5">已购课程词库掌握情况</p>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div
                        v-for="(c, index) in data.courseProgress"
                        :key="c.courseId"
                        class="course-card rounded-2xl bg-white/75 backdrop-blur-sm border border-zinc-100/80 p-4 hover:border-indigo-100 hover:shadow-sm transition-all"
                    >
                        <div class="flex items-start justify-between gap-3 mb-3">
                            <div class="min-w-0">
                                <p class="text-sm font-medium text-zinc-800 truncate">{{ c.name }}</p>
                                <p class="text-[11px] text-zinc-400 mt-0.5">
                                    已掌握 <span class="font-semibold text-zinc-600">{{ c.mastered }}</span>
                                    / {{ c.total }} 词
                                </p>
                            </div>
                            <span
                                class="shrink-0 text-xs font-bold tabular-nums px-2.5 py-1 rounded-lg bg-zinc-50 text-zinc-700"
                            >
                                {{ c.percent }}%
                            </span>
                        </div>
                        <div class="h-2.5 rounded-full bg-zinc-100 overflow-hidden">
                            <div
                                class="h-full rounded-full transition-all duration-700 ease-out"
                                :class="courseAccent(index)"
                                :style="{ width: `${Math.max(c.percent, c.mastered > 0 ? 2 : 0)}%` }"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </div>
</template>

<style scoped>
.dashboard-shell {
    animation: dashboard-in 0.45s ease-out both;
}

.stat-card {
    animation: dashboard-in 0.45s ease-out both;
}

.stat-card:nth-child(1) { animation-delay: 0.04s; }
.stat-card:nth-child(2) { animation-delay: 0.08s; }
.stat-card:nth-child(3) { animation-delay: 0.12s; }
.stat-card:nth-child(4) { animation-delay: 0.16s; }

.chart-panel {
    animation: dashboard-in 0.5s ease-out 0.12s both;
}

.course-card {
    animation: dashboard-in 0.45s ease-out 0.18s both;
}

@keyframes dashboard-in {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
