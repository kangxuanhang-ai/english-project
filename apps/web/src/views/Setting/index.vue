<template>
    <div class="mx-auto w-[1200px] px-4 py-6">
        <div class="flex items-center justify-between">
            <div>
                <div class="text-xl font-extrabold text-slate-900">设置</div>
                <div class="mt-1 text-sm text-slate-500">在这里修改你的个人信息与头像</div>
            </div>

            <div class="flex gap-2">
                <el-button @click="init">重置</el-button>
                <el-button @click="onSave" type="primary" :loading="saving">保存</el-button>
            </div>
        </div>
        <el-row v-loading="pageLoading" :gutter="16" class="mt-4">
            <el-col :span="8">
                <el-card shadow="never">
                    <template #header>
                        <div class="font-bold">头像</div>
                    </template>

                    <div class="flex items-center gap-4">
                        <img class="w-20 h-20 rounded-full object-cover border-2 border-gray-200"
                            :src="previewUrl || avatar" loading="lazy" referrerpolicy="no-referrer" />

                        <div class="flex flex-col gap-2">
                            <el-upload :show-file-list="false" :auto-upload="false" accept="image/*"
                                :on-change="onAvatarSelect">
                                <el-button type="primary">选择头像</el-button>
                            </el-upload>

                            <div class="text-xs text-slate-500">
                                支持 png/jpg/webp，建议小于 2MB
                            </div>
                        </div>
                    </div>
                </el-card>

                <el-card shadow="never" class="mt-4">
                    <template #header>
                        <div class="font-bold">账号</div>
                    </template>

                    <div class="text-sm text-slate-600">
                        <div class="flex items-center justify-between">
                            <span>登录状态</span>
                            <el-tag type="success">
                                已登录
                            </el-tag>
                        </div>
                    </div>
                </el-card>

                <el-card shadow="never" class="mt-4">
                    <template #header>
                        <div class="flex items-center justify-between">
                            <div class="font-bold">MCP 连接</div>
                            <el-button type="primary" size="small" @click="openCreateKey">生成新 Key</el-button>
                        </div>
                    </template>

                    <p class="text-sm text-slate-500 mb-3">
                        在 Claude Code 中连接 English 平台。配置方式与 LangSmith 相同，使用 HTTP MCP + API Key。
                    </p>

                    <el-table v-if="mcpKeys.length" :data="mcpKeys" size="small">
                        <el-table-column prop="keyPrefix" label="Key 前缀" min-width="160" />
                        <el-table-column prop="name" label="备注" min-width="80" />
                        <el-table-column prop="createdAt" label="创建时间" min-width="150" />
                        <el-table-column label="最后使用" min-width="120">
                            <template #default="{ row }">{{ row.lastUsedAt || '—' }}</template>
                        </el-table-column>
                        <el-table-column label="操作" width="70">
                            <template #default="{ row }">
                                <el-button type="danger" link @click="revokeKey(row.id)">吊销</el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                    <el-empty v-else description="暂无 MCP Key" :image-size="60" />
                </el-card>
            </el-col>

            <el-col :span="16">
                <el-card shadow="never">
                    <template #header>
                        <div class="font-bold">个人信息</div>
                    </template>

                    <el-form label-width="140px" :model="form" :rules="rules" ref="formRef" status-icon>
                        <el-form-item label="用户名：" prop="name">
                            <el-input v-model="form.name" placeholder="请输入用户名" clearable />
                        </el-form-item>

                        <el-form-item label="邮箱：" prop="email">
                            <el-input v-model="form.email" placeholder="请输入邮箱" clearable />
                        </el-form-item>

                        <el-form-item label="定时任务：" prop="isTimingTask">
                            <el-switch v-model="form.isTimingTask" />
                        </el-form-item>
                        <el-form-item label="定时任务时间：" prop="timingTaskTime">
                            <div>
                                <el-time-picker format="HH:mm:ss" value-format="HH:mm:ss" v-model="form.timingTaskTime"
                                    placeholder="请选择定时任务时间" />
                                <div class="text-xs text-slate-500 mt-3">tips:只有填写邮箱并且开启定时任务，才能收到每日打卡提醒</div>
                            </div>
                        </el-form-item>

                        <el-form-item label="地址：" prop="address">
                            <el-input v-model="form.address" placeholder="请输入地址" clearable />
                        </el-form-item>

                        <el-form-item label="签名：" prop="bio">
                            <el-input v-model="form.bio" placeholder="写点什么介绍一下自己" type="textarea" :rows="4"
                                maxlength="120" show-word-limit />
                        </el-form-item>
                    </el-form>
                </el-card>

                <el-card shadow="never" class="mt-4">
                    <template #header>
                        <div class="font-bold">危险操作</div>
                    </template>

                    <div class="flex items-center justify-between">
                        <div>
                            <div class="font-bold text-slate-900">退出登录</div>
                            <div class="text-sm text-slate-500">清除本地登录状态</div>
                        </div>
                        <el-button @click="logoutHandle" type="danger" plain>
                            退出
                        </el-button>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-dialog v-model="createKeyVisible" title="生成 MCP Key" width="420px">
            <el-input v-model="newKeyName" placeholder="备注（可选），如：我的 MacBook" maxlength="64" />
            <template #footer>
                <el-button @click="createKeyVisible = false">取消</el-button>
                <el-button type="primary" :loading="creatingKey" @click="submitCreateKey">生成</el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="keyRevealVisible" title="请保存 Key（仅显示一次）" width="560px">
            <el-alert type="warning" :closable="false" show-icon class="mb-3"
                title="关闭后将无法再次查看完整 Key，请立即复制。" />
            <el-input type="textarea" :rows="2" readonly :model-value="revealedKey" />
            <div class="mt-3 flex gap-2">
                <el-button @click="copyText(revealedKey)">复制 Key</el-button>
                <el-button type="primary" @click="copyText(revealedConfig)">复制 Claude 配置</el-button>
            </div>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted,useTemplateRef } from 'vue'
import type { UserUpdate } from '@en/common/user'
import type { FormRules } from 'element-plus'
import avatar from '@/assets/images/avatar/default-avatar.png'
import { useUserStore } from '@/stores/user'
import { uploadAvatar } from '@/apis/user' //上传头像接口
import type { UploadFile,FormInstance } from 'element-plus' //上传文件类型
import { updateUser } from '@/apis/user' //更新用户信息接口
import { ElMessage,ElMessageBox } from 'element-plus' //提示信息
import { useAvatar } from '@/hooks/useAvatar'
import { useLogin } from '@/hooks/useLogin'
import { createMcpKey, listMcpKeys, revokeMcpKey } from '@/apis/mcp-keys'
import type { McpApiKeyItem } from '@en/common/mcp'
const { customAvatar } = useAvatar()
const { logout } = useLogin()
const formRef = useTemplateRef<FormInstance>('formRef') //表单ref
const userStore = useUserStore()
const previewUrl = ref<string>('')
const pageLoading = ref(true)
const saving = ref(false)
const mcpKeys = ref<McpApiKeyItem[]>([])
const createKeyVisible = ref(false)
const keyRevealVisible = ref(false)
const newKeyName = ref('')
const creatingKey = ref(false)
const revealedKey = ref('')
const revealedConfig = ref('')
const form = ref<UserUpdate>({
    name: '', //用户名
    email: '', //邮箱
    isTimingTask: false, //是否开启定时任务
    timingTaskTime: '',//定时任务时间
    address: '',//地址
    bio: '',//签名
    avatar: ''//头像
})
//上传头像
const onAvatarSelect = async (file: UploadFile) => {
    try {
        const formData = new FormData()
        formData.append('file', file.raw as File)
        const res = await uploadAvatar(formData)
        if (res.success && res.data) {
            form.value.avatar = res.data.databaseUrl
            previewUrl.value = res.data.previewUrl
        } else {
            ElMessage.error(res.message || '上传头像失败')
        }
    } catch {
        ElMessage.error('上传头像失败，请重试')
    }
}
//表单验证规则
const rules: FormRules = {
    name: [
        { required: true, message: '请输入用户名', trigger: 'blur' }
    ],
    email: [
        { required: false, message: '请输入邮箱', trigger: 'blur' },
        {
            validator: (rule, value, callback) => {
                if (value && !/^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/.test(value)) {
                    callback(new Error('请输入正确的邮箱'))
                } else {
                    callback()
                }
            }, trigger: 'blur'
        }
    ],
    isTimingTask: [
        { required: true, message: '请选择是否开启定时任务', trigger: 'blur', type: 'boolean' }
    ],
    timingTaskTime: [
        { required: true, message: '请选择定时任务时间', trigger: 'blur' }
    ]
}
//提交保存接口的
const onSave = async () => {
    try {
        await formRef.value?.validate()
    } catch {
        return
    }
    saving.value = true
    try {
        const res = await updateUser(form.value)
        if (res.success && res.data) {
            userStore.updateUser(res.data)
            ElMessage.success('更新成功')
        } else {
            ElMessage.error(res.message || '保存失败')
        }
    } catch {
        ElMessage.error('保存失败，请重试')
    } finally {
        saving.value = false
    }
}
//退出登录
const logoutHandle = () => {
    ElMessageBox.confirm('确定退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
    }).then(() => {
        logout()
    })
}

const init = () => {
    //如果用户登录了，则获取用户信息
    if(userStore.getUser) {
        form.value = {...userStore.getUpdateUserInfo}
        previewUrl.value = customAvatar(form.value.avatar!)
        loadMcpKeys()
    }
}

const loadMcpKeys = async () => {
    try {
        const res = await listMcpKeys()
        if (res.success && res.data) {
            mcpKeys.value = res.data
        }
    } catch {
        /* 设置页次要功能，静默失败 */
    }
}

const openCreateKey = () => {
    newKeyName.value = ''
    createKeyVisible.value = true
}

const submitCreateKey = async () => {
    creatingKey.value = true
    try {
        const res = await createMcpKey({ name: newKeyName.value })
        if (res.success && res.data) {
            createKeyVisible.value = false
            revealedKey.value = res.data.key
            revealedConfig.value = JSON.stringify(res.data.claudeConfig, null, 2)
            keyRevealVisible.value = true
            await loadMcpKeys()
        } else {
            ElMessage.error(res.message || '生成失败')
        }
    } catch {
        ElMessage.error('生成失败，请重试')
    } finally {
        creatingKey.value = false
    }
}

const revokeKey = (keyId: string) => {
    ElMessageBox.confirm('吊销后使用该 Key 的 Claude 配置将失效，确定继续？', '吊销 Key', {
        type: 'warning',
    }).then(async () => {
        const res = await revokeMcpKey(keyId)
        if (res.success) {
            ElMessage.success('已吊销')
            await loadMcpKeys()
        } else {
            ElMessage.error(res.message || '吊销失败')
        }
    })
}

const copyText = async (text: string) => {
    try {
        await navigator.clipboard.writeText(text)
        ElMessage.success('已复制')
    } catch {
        ElMessage.error('复制失败')
    }
}

onMounted(() => {
    try {
        init()
    } catch {
        ElMessage.error('加载用户信息失败')
    } finally {
        pageLoading.value = false
    }
})
</script>