<template>
    <div class="w-[1200px] mx-auto mt-10 bg-linear-to-br from-emerald-50 to-teal-50 rounded-[20px] p-20 shadow-lg">
        <div class="flex items-center justify-between mb-8">
            <div>
                <div class="flex items-center gap-2">
                    <el-icon color="#059669" size="20">
                        <Notebook />
                    </el-icon>
                    <span class="text-2xl font-bold text-gray-800">我的生词本</span>
                </div>
                <div class="text-sm text-gray-600 mt-1">复习中的词与已掌握词分开管理</div>
            </div>
        </div>

        <el-tabs v-model="activeTab" @tab-change="onTabChange">
            <el-tab-pane label="复习中" name="learning" />
            <el-tab-pane label="已掌握" name="mastered" />
        </el-tabs>

        <div v-if="isLoading" class="grid grid-cols-3 gap-3 mt-6">
            <div v-for="n in 6" :key="n" class="bg-white border border-emerald-100 rounded-[10px] p-4 min-h-[220px] animate-pulse" />
        </div>

        <div v-else-if="list.length === 0" class="py-16">
            <el-empty :description="activeTab === 'learning' ? '暂无复习中的单词' : '暂无已掌握单词'" />
        </div>

        <div v-else class="grid grid-cols-3 gap-3 mt-6">
            <div
                v-for="item in list"
                :key="item.wordId"
                class="bg-white border border-emerald-200 rounded-[10px] p-4 shadow-sm min-h-[220px] flex flex-col"
            >
                <div class="text-base font-semibold text-emerald-700 mb-1">{{ item.word }}</div>
                <div class="text-sm text-gray-500 mb-2">{{ item.phonetic }}</div>
                <div
                    v-html="formatWordField(item.definition)"
                    class="text-sm text-gray-700 mb-1 overflow-hidden line-clamp-3"
                />
                <div
                    v-html="formatWordField(item.translation)"
                    class="text-sm text-gray-600 overflow-hidden line-clamp-2 flex-1"
                />
                <div class="flex gap-2 mt-3">
                    <el-button
                        v-if="activeTab === 'learning'"
                        size="small"
                        type="primary"
                        :loading="masteringId === item.wordId"
                        @click="handleMaster(item.wordId)"
                    >
                        标记掌握
                    </el-button>
                    <el-button
                        v-if="activeTab === 'learning'"
                        size="small"
                        :loading="removingId === item.wordId"
                        @click="handleRemove(item.wordId)"
                    >
                        移除
                    </el-button>
                </div>
            </div>
        </div>

        <el-pagination
            v-if="total > 0"
            class="mt-10 justify-center"
            background
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            @current-change="loadList"
            @size-change="loadList"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Notebook } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { MyWord } from '@en/common/word'
import { getMyWords, markMyWordsMastered, removeMyWord } from '@/apis/my-words'
import { useUserStore } from '@/stores/user'
import { formatWordField } from '@/utils/formatWordField'

const userStore = useUserStore()
const activeTab = ref<'learning' | 'mastered'>('learning')
const isLoading = ref(false)
const list = ref<MyWord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const masteringId = ref<string | null>(null)
const removingId = ref<string | null>(null)

const loadList = async () => {
    try {
        isLoading.value = true
        const res = await getMyWords({
            status: activeTab.value,
            page: page.value,
            pageSize: pageSize.value,
        })
        if (res.success) {
            list.value = res.data.list
            total.value = res.data.total
        }
    } catch {
        ElMessage.error('加载生词本失败')
    } finally {
        isLoading.value = false
    }
}

const onTabChange = () => {
    page.value = 1
    loadList()
}

const handleMaster = async (wordId: string) => {
    try {
        masteringId.value = wordId
        const res = await markMyWordsMastered({ wordIds: [wordId] })
        if (res.success) {
            userStore.updateUserWordNumber(res.data.wordNumber)
            ElMessage.success('已标记掌握')
            await loadList()
        }
    } catch {
        ElMessage.error('标记失败')
    } finally {
        masteringId.value = null
    }
}

const handleRemove = async (wordId: string) => {
    try {
        removingId.value = wordId
        const res = await removeMyWord(wordId)
        if (res.success) {
            ElMessage.success('已移除')
            await loadList()
        }
    } catch {
        ElMessage.error('移除失败')
    } finally {
        removingId.value = null
    }
}

onMounted(() => {
    loadList()
})
</script>
