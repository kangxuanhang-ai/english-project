import layout from '@/layout/index.vue'

export default [
    {
        path: '/courses', //路由后面多个s
        component: layout,
        children: [
            { path: 'index', component: () => import('@/views/Course/index.vue') },
            { path: 'learn/:courseId/:title', component: () => import('@/views/Course/Learn/index.vue'), meta: { requiresAuth: true } },
        ]
    }
]