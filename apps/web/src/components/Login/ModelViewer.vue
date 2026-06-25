<template>
    <div ref="containerRef" class="relative w-[800px] h-full bg-linear-to-br from-gray-800 to-gray-900">
        <div v-if="!isLoaded" class="absolute inset-0 z-10 flex items-center justify-center">
            <div class="text-gray-400 text-sm">加载中...</div>
        </div>
        <div v-if="loadError" class="absolute inset-0 z-10 flex items-center justify-center px-6 text-center">
            <p class="text-gray-400 text-sm">3D 模型加载失败，请刷新重试</p>
        </div>
        <canvas class="w-full h-full block" ref="canvasRef"></canvas>
        <div class="absolute top-6 left-6 z-20 pointer-events-none">
            <div class="flex items-center gap-2">
                <div
                    class="w-10 h-10 bg-linear-to-br from-indigo-500 to-purple-600 rounded-[10px] flex items-center justify-center">
                    <span class="text-white font-bold text-xl">E</span>
                </div>
                <span class="text-white text-xl font-bold">English App</span>
            </div>
        </div>
        <div class="absolute top-6 right-6 z-20">
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

const containerRef = useTemplateRef<HTMLDivElement>('containerRef')
const canvasRef = useTemplateRef<HTMLCanvasElement>('canvasRef')
const type = ref<LoginType>('login')
const isLoaded = ref(false)
const loadError = ref(false)

let THREE: any = null
let GLTFLoaderClass: any = null
let OrbitControlsClass: any = null
let renderer: any = null
let controls: any = null
let scene: any = null
let camera: any = null
let clock: any = null
let currentModel: any = null
let mixer: any = null
let animationId = 0
let resizeObserver: ResizeObserver | null = null
let disposed = false

function disposeThree() {
    disposed = true
    resizeObserver?.disconnect()
    resizeObserver = null
    if (animationId) {
        cancelAnimationFrame(animationId)
        animationId = 0
    }
    controls?.dispose()
    controls = null
    if (renderer) {
        renderer.dispose()
        renderer = null
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
        scene = null
    }
}

const loginClass = computed(() => {
    return type.value === 'login' ? 'bg-indigo-500 text-white shadow-lg px-4 py-2 rounded-md text-sm font-medium transition-all' : 'text-white/70 hover:text-white hover:bg-white/10 px-4 py-2 rounded-md text-sm font-medium transition-all'
})
const registerClass = computed(() => {
    return type.value === 'register' ? 'bg-indigo-500 text-white shadow-lg px-4 py-2 rounded-md text-sm font-medium transition-all' : 'text-white/70 hover:text-white hover:bg-white/10 px-4 py-2 rounded-md text-sm font-medium transition-all'
})
const emits = defineEmits(['changeType'])

function getSize() {
    const el = containerRef.value
    return {
        width: el?.clientWidth || 800,
        height: el?.clientHeight || 700,
    }
}

function resizeRenderer() {
    if (!renderer || !camera) return
    const { width, height } = getSize()
    if (width <= 0 || height <= 0) return
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
}

function addLights() {
    const ambient = new THREE.AmbientLight(0xffffff, 1.2)
    scene.add(ambient)
    const key = new THREE.DirectionalLight(0xffffff, 2)
    key.position.set(5, 10, 7.5)
    scene.add(key)
    const fill = new THREE.DirectionalLight(0xaabbff, 0.6)
    fill.position.set(-4, 2, -3)
    scene.add(fill)
}

const loadModel = (url: LoginType) => {
    if (!GLTFLoaderClass || !scene) return
    if (currentModel) {
        scene.remove(currentModel)
        currentModel = null
    }
    mixer = null
    loadError.value = false

    const loader = new GLTFLoaderClass()
    type.value = url
    const modelPath = url === 'login' ? '/models/login/scene.gltf' : '/models/register/scene.gltf'

    loader.load(
        modelPath,
        (gltf: any) => {
            if (disposed) return
            currentModel = gltf.scene
            scene.add(currentModel)
            currentModel.position.y = -0.8
            currentModel.scale.set(0.8, 0.8, 0.8)
            if (gltf.animations?.length > 0) {
                mixer = new THREE.AnimationMixer(currentModel)
                gltf.animations.forEach((animation: any) => {
                    mixer!.clipAction(animation).play()
                })
            }
            isLoaded.value = true
        },
        undefined,
        () => {
            if (disposed) return
            loadError.value = true
            isLoaded.value = true
        },
    )
    emits('changeType', url)
}

onMounted(async () => {
    THREE = await import('three')
    const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js')
    const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
    if (disposed) return
    GLTFLoaderClass = GLTFLoader
    OrbitControlsClass = OrbitControls

    scene = new THREE.Scene()
    clock = new THREE.Timer()
    addLights()

    const { width, height } = getSize()
    camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
    camera.position.set(1, 0.5, 1)

    renderer = new THREE.WebGLRenderer({
        canvas: canvasRef.value!,
        antialias: true,
        alpha: true,
        precision: 'highp',
        powerPreference: 'high-performance',
    })
    resizeRenderer()

    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true

    loadModel(type.value)

    const animate = () => {
        if (disposed) return
        animationId = requestAnimationFrame(animate)
        if (mixer) {
            mixer.update(clock.getDelta())
        }
        if (currentModel) {
            currentModel.rotation.y += 0.002
        }
        controls?.update()
        renderer?.render(scene, camera)
    }
    animate()

    resizeObserver = new ResizeObserver(() => resizeRenderer())
    if (containerRef.value) {
        resizeObserver.observe(containerRef.value)
    }
})

onUnmounted(() => {
    disposeThree()
})
</script>
