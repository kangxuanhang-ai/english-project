<template>
    <div class="w-[1200px] mx-auto mt-10 bg-linear-to-br from-blue-50 to-indigo-50 rounded-[20px] p-20 shadow-lg">
        <div class="h-20">
            <div class="flex items-center gap-2">
                <el-icon color="#2563EB" size="20">
                    <Reading />
                </el-icon>
                <span class="text-2xl font-bold text-gray-800">词库列表</span>
            </div>
            <div class="text-sm text-gray-600">词典来源：牛津、柯林斯、BNC、FRQ、高考、中考、GRE、TOEFL、IELTS、大学英语六级、大学英语四级、考研</div>
        </div>
        <div class="flex items-center mb-10">
            <el-input @keyup.enter="searchWord" class="mr-10" v-model="query.word" placeholder="请输入单词"></el-input>
            <el-checkbox v-model="query.gk">高考</el-checkbox>
            <el-checkbox v-model="query.zk">中考</el-checkbox>
            <el-checkbox v-model="query.gre">GRE</el-checkbox>
            <el-checkbox v-model="query.toefl">TOEFL</el-checkbox>
            <el-checkbox v-model="query.ielts">IELTS</el-checkbox>
            <el-checkbox v-model="query.cet6">六级</el-checkbox>
            <el-checkbox v-model="query.cet4">四级</el-checkbox>
            <el-checkbox v-model="query.ky">考研</el-checkbox>
            <el-button @click="searchWord" class="ml-10" type="primary">搜索</el-button>
        </div>
        <div v-if="isLoading" class="grid grid-cols-3 gap-3">
            <div v-for="n in 6" :key="n" class="bg-white border border-blue-100 rounded-[10px] p-4 min-h-[240px] animate-pulse">
                <div class="h-4 bg-blue-100 rounded w-1/3 mb-3" />
                <div class="h-3 bg-zinc-100 rounded w-full mb-2" />
                <div class="h-3 bg-zinc-100 rounded w-5/6" />
            </div>
        </div>
        <template v-else>
            <div class="grid grid-cols-3 gap-3">
                <div
                    class="bg-white hover:bg-blue-50 border border-blue-200 text-gray-800 rounded-[10px] p-4 transition-all duration-200 shadow-sm hover:shadow-md min-h-[240px] flex flex-col"
                    v-for="item in list"
                    :key="item.id"
                >
                    <div class="flex-1 min-h-0">
                        <div class="text-base font-semibold text-blue-600 mb-1">{{ item.word }}</div>
                        <div class="text-sm text-gray-500 mb-2 flex items-center gap-2">
                            {{ item.phonetic }}
                            <el-icon size="18" color="#2563EB" class="cursor-pointer" @click="playAudio(item.word)">
                                <VideoPlay />
                            </el-icon>
                        </div>
                        <div
                            v-html="formatWordField(item.definition)"
                            class="text-sm text-gray-700 mb-1 overflow-hidden line-clamp-3"
                        />
                        <div
                            v-html="formatWordField(item.translation)"
                            class="text-sm text-gray-600 mb-2 overflow-hidden line-clamp-2"
                        />
                        <div class="flex items-center gap-1.5 flex-wrap">
                            <el-tag v-if="item.gk" type="info" size="small" effect="plain">高考</el-tag>
                            <el-tag v-if="item.zk" type="info" size="small" effect="plain">中考</el-tag>
                            <el-tag v-if="item.gre" type="info" size="small" effect="plain">GRE</el-tag>
                            <el-tag v-if="item.toefl" type="info" size="small" effect="plain">TOEFL</el-tag>
                            <el-tag v-if="item.ielts" type="info" size="small" effect="plain">IELTS</el-tag>
                            <el-tag v-if="item.cet6" type="info" size="small" effect="plain">六级</el-tag>
                            <el-tag v-if="item.cet4" type="info" size="small" effect="plain">四级</el-tag>
                            <el-tag v-if="item.ky" type="info" size="small" effect="plain">考研</el-tag>
                        </div>
                    </div>
                    <el-button
                        size="small"
                        type="primary"
                        plain
                        class="mt-3 self-start"
                        :loading="addingWord === item.word"
                        @click.stop="handleAddToMyWords(item.word)"
                    >
                        加入生词本
                    </el-button>
                </div>
            </div>
            <el-pagination
                class="mt-10 justify-center"
                background
                v-model:current-page="query.page"
                v-model:page-size="query.pageSize"
                :total="total"
                @current-change="getList"
                @size-change="getList"
            />
        </template>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getWordBookList } from '@/apis/word-book'
import type { WordQuery, WordList } from '@en/common/word'
import { Reading, VideoPlay } from '@element-plus/icons-vue'
import { useAudio } from '@/hooks/useAudio'
import { useLogin } from '@/hooks/useLogin'
import { addMyWords } from '@/apis/my-words'
import { ElMessage } from 'element-plus'
import { formatWordField } from '@/utils/formatWordField'

const { playAudio } = useAudio({})
const { login } = useLogin()
const addingWord = ref<string | null>(null)
const isLoading = ref(false)
const total = ref<WordList['total']>(0)
const list = ref<WordList['list']>([])
const query = ref<WordQuery>({
    page: 1,
    pageSize: 12,
    word: '',
    gk: false,
    zk: false,
    gre: false,
    toefl: false,
    ielts: false,
    cet6: false,
    cet4: false,
    ky: false,
})
const searchWord = () => {
    query.value.page = 1 //重置一下页数
    getList() //重新获取列表
}

const getList = async () => {
    try {
        isLoading.value = true;
        const res = await getWordBookList(query.value)
        if (res.success) {
            total.value = res.data.total
            list.value = res.data.list
        }
    } catch (error) {
        ElMessage.error('加载词库列表失败');
    } finally {
        isLoading.value = false;
    }
}

const handleAddToMyWords = async (word: string) => {
    const ok = await login()
    if (!ok) return
    try {
        addingWord.value = word
        const res = await addMyWords({ words: [word] })
        if (res.success) {
            if (res.data.added.length) {
                ElMessage.success(`已加入生词本：${word}`)
            } else if (res.data.skipped.length) {
                ElMessage.warning(res.data.skipped[0])
            }
        }
    } catch {
        ElMessage.error('加入生词本失败')
    } finally {
        addingWord.value = null
    }
}


onMounted(() => {
    getList()
})
</script>
