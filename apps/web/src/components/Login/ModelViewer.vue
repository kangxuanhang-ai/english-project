<template>
    <div class="relative w-[800px] h-full bg-linear-to-br from-gray-800 to-gray-900">
        <div v-if="!isLoaded" class="w-full h-full flex items-center justify-center">
            <div class="text-gray-400 text-sm">加载中...</div>
        </div>
        <canvas v-show="isLoaded" class="w-full h-full" ref="canvasRef"></canvas>
        <div class="absolute top-6 left-6">
            <div class="flex items-center gap-2">
                <div
                    class="w-10 h-10 bg-linear-to-br from-indigo-500 to-purple-600 rounded-[10px] flex items-center justify-center">
                    <span class="text-white font-bold text-xl">E</span>
                </div>
                <span class="text-white text-xl font-bold">English App</span>
            </div>
        </div>
        <!-- 登录/注册切换按钮 -->
        <div class="absolute top-6 right-6">
            <div class="flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-lg p-1">
                <button @click="loadModel('login')" :class="loginClass">
                    登录
                </button>
                <button @click="loadModel('register')" :class="registerClass">
                    注册
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, useTemplateRef } from 'vue'
import type { LoginType } from './type'

const canvasRef = useTemplateRef<HTMLCanvasElement>('canvasRef')
const type = ref<LoginType>('login')
const isLoaded = ref(false)

let THREE: any = null
let GLTFLoaderClass: any = null
let OrbitControlsClass: any = null
let renderer: any = null
let controls: any = null
let scene: any = null
let clock: any = null
let currentModel: any = null
let mixer: any = null
let animationId: number = 0

const loginClass = computed(() => {
    return type.value === 'login' ? 'bg-indigo-500 text-white shadow-lg px-4 py-2 rounded-md text-sm font-medium transition-all' : 'text-white/70 hover:text-white hover:bg-white/10 px-4 py-2 rounded-md text-sm font-medium transition-all'
})
const registerClass = computed(() => {
    return type.value === 'register' ? 'bg-indigo-500 text-white shadow-lg px-4 py-2 rounded-md text-sm font-medium transition-all' : 'text-white/70 hover:text-white hover:bg-white/10 px-4 py-2 rounded-md text-sm font-medium transition-all'
})
const emits = defineEmits(['changeType'])

const loadModel = (url: LoginType) => {
    if (currentModel) {
        scene.remove(currentModel)
        currentModel = null
    }
    const loader = new GLTFLoaderClass()
    type.value = url
    if (url === 'login') {
        loader.load('/models/login/scene.gltf', (gltf: any) => {
            currentModel = gltf.scene
            scene.add(currentModel)
            scene.position.y = -0.8
            currentModel.scale.set(0.8, 0.8, 0.8)
        })
    }
    if (url === 'register') {
        loader.load('/models/register/scene.gltf', (gltf: any) => {
            currentModel = gltf.scene
            scene.add(currentModel)
            scene.position.y = -0.8
            currentModel.scale.set(0.8, 0.8, 0.8)
            if(gltf.animations && gltf.animations.length > 0) {
                mixer = new THREE.AnimationMixer(currentModel)
                gltf.animations.forEach((animation: any) => {
                    mixer!.clipAction(animation).play()
                })
            }
        })
    }
    emits('changeType', url)
}

onMounted(async () => {
    THREE = await import('three')
    const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js')
    const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
    GLTFLoaderClass = GLTFLoader
    OrbitControlsClass = OrbitControls

    scene = new THREE.Scene()
    clock = new THREE.Timer()

    const width = canvasRef.value!.clientWidth
    const height = canvasRef.value!.clientHeight
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
    camera.position.set(1, 0.5, 1)
    renderer = new THREE.WebGLRenderer({
        canvas: canvasRef.value!,
        antialias: true,
        alpha: true,
        precision: 'highp',
        powerPreference: 'high-performance',
    })
    loadModel(type.value)
    renderer.setSize(width, height)
    renderer.render(scene, camera)
    controls = new OrbitControls(camera, renderer.domElement)
    const animate = () => {
        animationId = requestAnimationFrame(animate)
        if(mixer) {
            mixer.update(clock.getDelta())
        }
        scene.rotation.y += 0.002
        controls!.update()
        renderer!.render(scene, camera)
    }
    animate()

    isLoaded.value = true
})

onUnmounted(() => {
    cancelAnimationFrame(animationId)
    controls?.dispose()
    if (renderer) {
        renderer.dispose()
        renderer.domElement.remove()
    }
    if (scene) {
        scene.traverse((object: any) => {
            if (object.isMesh) {
                object.geometry.dispose()
                if (Array.isArray(object.material)) {
                    object.material.forEach((material: any) => material.dispose())
                } else {
                    object.material.dispose()
                }
            }
        })
    }
})
</script>
