<template>
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-2">欢迎注册</h1>
        <p class="text-gray-500 text-sm">请填写以下信息以完成注册</p>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80" label-position="top" class="space-y-6">
        <el-form-item  prop="name">
            <el-input v-model="form.name" placeholder="请输入用户名" size="large" class="h-12" :prefix-icon="User" />
        </el-form-item>
        <el-form-item  prop="phone">
            <el-input :maxlength="11" v-model="form.phone" placeholder="请输入手机号" size="large" class="h-12" :prefix-icon="User" />
        </el-form-item>
        <el-form-item  prop="email">
            <el-input v-model="form.email" placeholder="请输入邮箱(可选)" size="large" class="h-12" :prefix-icon="User" />
        </el-form-item>
        <el-form-item  prop="password">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" class="h-12"
                :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item class="pt-4">
            <el-button type="primary" size="large" :loading="isSubmitting"
                class="w-full h-12 text-base font-semibold bg-linear-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 border-0"
                @click="handleRegister">
                注册
            </el-button>
        </el-form-item>
    </el-form>
</template>


<script setup lang="ts">
import { ref,useTemplateRef,toRaw } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { register } from '@/apis/user' //注册接口
import type { UserRegister } from '@en/common/user' //注册类型
import md5 from 'md5' //md5加密
import type { FormInstance } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useLogin } from '@/hooks/useLogin'
const { hide } = useLogin()
const formRef = useTemplateRef<FormInstance>('formRef')
const userStore = useUserStore()
const isSubmitting = ref(false)
const form = ref<UserRegister>({
    name: '',
    phone: '',
    email: '',
    password: '',
})

const rules = {
    name: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 2, max: 10, message: '用户名长度为2-10位', trigger: 'blur' },
    ],
    phone: [
        { required: true, message: '请输入手机号', trigger: 'blur' },
        { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
    ],
    password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, max: 16, message: '密码长度为6-16位', trigger: 'blur' },
    ],
}

const handleRegister = async () => {
    try {
        await formRef.value?.validate()
        isSubmitting.value = true
        const email = form.value.email?.trim()
        const res = await register({
            name: form.value.name,
            phone: form.value.phone,
            password: toRaw(md5(form.value.password)),
            ...(email ? { email } : {}),
        })
        if (res.code === 200) {
            userStore.setUser(res.data)
            ElMessage.success('注册成功')
            hide()
        } else {
            ElMessage.error(res.message)
        }
    } catch (error: unknown) {
        if (error !== false) {
            const msg = (error as { response?: { data?: { message?: string } } })?.response?.data?.message
            ElMessage.error(msg || '注册失败，请稍后重试')
        }
    } finally {
        isSubmitting.value = false
    }
}
</script>