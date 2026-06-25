<template>
    <div>
        <div v-if="!isLoaded" class="w-[500px] h-[250px] bg-gray-900/50 rounded-lg flex items-center justify-center">
            <div class="text-gray-400 text-sm">加载中...</div>
        </div>
        <canvas ref="hologramRef" v-show="isLoaded"></canvas>
    </div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef, onMounted, onUnmounted } from 'vue'

const isLoaded = ref(false)
const hologramRef = useTemplateRef<HTMLCanvasElement>('hologramRef')

let renderer: any = null
let controls: any = null
let scene: any = null
let animationId = 0
let disposed = false

function disposeScene() {
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
        scene.traverse((obj: any) => {
            if (obj.isMesh) {
                obj.geometry.dispose()
                if (Array.isArray(obj.material)) {
                    obj.material.forEach((m: any) => m.dispose())
                } else {
                    obj.material.dispose()
                }
            }
        })
        scene = null
    }
}

onUnmounted(() => {
    disposed = true
    disposeScene()
})

onMounted(async () => {
    const THREE = await import('three')
    const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js')
    const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
    if (disposed || !hologramRef.value) return

    scene = new THREE.Scene()
    let mixer: InstanceType<typeof THREE.AnimationMixer> | null = null
    const clock = new THREE.Timer()
    const camera = new THREE.PerspectiveCamera(75, 500 / 250, 0.1, 1000)
    camera.position.set(0, 0, 10)
    const loader = new GLTFLoader()

    loader.load('/models/hologram/scene.gltf', (gltf: any) => {
        if (disposed || !scene) return
        scene.add(gltf.scene)
        gltf.scene.scale.set(4, 4, 4)
        if(gltf.animations && gltf.animations.length > 0) {
            mixer = new THREE.AnimationMixer(gltf.scene)
            gltf.animations.forEach((clip: any) => {
                mixer!.clipAction(clip).play()
            })
        }
    })

    const ambientLight = new THREE.AmbientLight(0xffffff, 1)
    scene.add(ambientLight)
    const directionalLight = new THREE.DirectionalLight(0xffffff, 2)
    directionalLight.position.set(5, 10, 7.5)
    scene.add(directionalLight)

    renderer = new THREE.WebGLRenderer({
        canvas: hologramRef.value,
        antialias: true,
        alpha: true,
        precision: 'highp',
        powerPreference: 'high-performance',
    })
    renderer.setSize(500, 250)
    controls = new OrbitControls(camera, renderer.domElement)

    const animate = () => {
        if (disposed) return
        animationId = requestAnimationFrame(animate)
        const delta = clock.getDelta()
        if(mixer) {
            mixer.update(delta)
        }
        scene!.rotation.y += 0.002
        controls!.update()
        renderer!.render(scene!, camera)
    }
    animate()

    isLoaded.value = true
})
</script>
