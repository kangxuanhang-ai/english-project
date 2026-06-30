import layout from '@/layout/index.vue'

export default [
    {
        path: '/my-words',
        component: layout,
        children: [
            {
                path: '',
                component: () => import('@/views/MyWords/index.vue'),
                meta: { requiresAuth: true },
            },
        ],
    },
]
