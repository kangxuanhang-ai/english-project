import layout from '@/layout/index.vue'

export default [
    {
        path: '/chat',
        component: layout,
        children: [
            { path: '', redirect: '/chat/normal' },
            { path: ':role/:conversationId?', component: () => import('@/views/Chat/index.vue'), meta: { requiresAuth: true } },
        ]
    }
]