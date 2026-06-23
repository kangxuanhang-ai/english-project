<template>
   <canvas ref="hologramRef"></canvas>
</template>


<script setup lang="ts">
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js' //gltf模型加载器
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js' //轨道控制器
//轨道控制器 模型他可以被退拽 缩放 旋转
import { useTemplateRef, onMounted, onUnmounted } from 'vue'

let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let scene: THREE.Scene | null = null
let animationId: number

onUnmounted(() => {
    if (animationId) cancelAnimationFrame(animationId)
    if (controls) controls.dispose()
    if (renderer) {
        renderer.dispose()
        renderer.domElement.remove()
    }
    if (scene) {
        scene.traverse((obj) => {
            if ((obj as any).isMesh) {
                const mesh = obj as THREE.Mesh
                mesh.geometry.dispose()
                if (Array.isArray(mesh.material)) {
                    mesh.material.forEach(m => m.dispose())
                } else {
                    mesh.material.dispose()
                }
            }
        })
    }
})
const hologramRef = useTemplateRef<HTMLCanvasElement>('hologramRef')
const initThree = () => {

    //创建场景 -> 网格(几何 + 材质) + 相机 + 渲染器 + 灯光(可选的)
    //创建场景 -> 模型obj gltf ... + 相机 + 渲染器 + 灯光(可选的)
    scene = new THREE.Scene()
    //动画混合器
    let mixer: THREE.AnimationMixer | null = null
    const clock = new THREE.Timer() //创建时钟
    //创建相机
    const camera = new THREE.PerspectiveCamera(75, 500 / 250, 0.1, 1000)
    camera.position.set(0, 0, 10)
    const loader = new GLTFLoader() //创建模型加载器

    loader.load('/models/hologram/scene.gltf', (gltf) => {
        scene!.add(gltf.scene) //添加模型到场景
        gltf.scene.scale.set(4, 4, 4) //缩放模型
        if(gltf.animations && gltf.animations.length > 0) {
            mixer = new THREE.AnimationMixer(gltf.scene)
            gltf.animations.forEach((clip) => {
                const action = mixer!.clipAction(clip)
                action.play()
            })
        }
    })
    //环境光
    const ambientLight = new THREE.AmbientLight(0xffffff, 1)
    scene.add(ambientLight)
    //平行光
    const directionalLight = new THREE.DirectionalLight(0xffffff, 2)
    directionalLight.position.set(5, 10, 7.5)
    scene.add(directionalLight)
    //创建渲染器
    renderer = new THREE.WebGLRenderer({
        canvas: hologramRef.value!,
        antialias: true, //抗锯齿
        alpha: true, //透明背景
        precision: 'highp', //高精度
        powerPreference: 'high-performance', //高性能
    })
    renderer.setSize(500, 250) //设置渲染器大小
    controls = new OrbitControls(camera, renderer.domElement) //创建轨道控制器
    const animate = () => {
        animationId = requestAnimationFrame(animate)
        const delta = clock.getDelta() //1 - 2
        if(mixer) {
            mixer.update(delta) //更新动画混合器
        }
        scene!.rotation.y += 0.002 //旋转场景
        controls!.update() //更新轨道控制器
        renderer!.render(scene!, camera)
    }
    animate()
}
onMounted(()=>{
    initThree()
})
</script>