<script setup lang="ts">
import type { ChatGrammarBlock } from '@en/common/chat'

defineProps<{
    data: ChatGrammarBlock
}>()
</script>

<template>
    <div class="grammar-block">
        <div v-if="data.ok" class="grammar-block__ok">
            <span class="grammar-block__ok-icon">✓</span>
            <span>{{ data.summary ?? '语法正确，没有发现错误。' }}</span>
        </div>

        <template v-else>
            <div v-if="data.error" class="grammar-block__tag">{{ data.error }}</div>

            <div v-if="data.original || data.corrected" class="grammar-block__compare">
                <div v-if="data.original" class="grammar-block__line grammar-block__line--wrong">
                    <span class="grammar-block__label">原句</span>
                    <span class="grammar-block__text">{{ data.original }}</span>
                </div>
                <div v-if="data.original && data.corrected" class="grammar-block__arrow">↓</div>
                <div v-if="data.corrected" class="grammar-block__line grammar-block__line--right">
                    <span class="grammar-block__label">修正</span>
                    <span class="grammar-block__text">{{ data.corrected }}</span>
                </div>
            </div>

            <p v-if="data.explanation" class="grammar-block__hint">{{ data.explanation }}</p>
        </template>
    </div>
</template>

<style scoped>
.grammar-block {
    margin-top: 0.75rem;
    padding: 0.875rem;
    border-radius: 12px;
    border: 1px solid color-mix(in srgb, var(--chat-accent-border) 65%, transparent);
    background: linear-gradient(160deg, #fafaf9 0%, #fff 100%);
}

.grammar-block__ok {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    font-weight: 600;
    color: #047857;
}

.grammar-block__ok-icon {
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6875rem;
    background: #d1fae5;
    color: #047857;
}

.grammar-block__tag {
    display: inline-block;
    margin-bottom: 0.625rem;
    padding: 0.25rem 0.625rem;
    border-radius: 999px;
    font-size: 0.6875rem;
    font-weight: 700;
    color: #b45309;
    background: #fffbeb;
    border: 1px solid #fde68a;
}

.grammar-block__compare {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.grammar-block__line {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.625rem 0.75rem;
    border-radius: 10px;
    font-size: 0.8125rem;
    line-height: 1.5;
}

.grammar-block__line--wrong {
    background: #fef2f2;
    border: 1px solid #fecaca;
}

.grammar-block__line--right {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
}

.grammar-block__label {
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #78716c;
}

.grammar-block__line--wrong .grammar-block__text {
    color: #991b1b;
    text-decoration: line-through;
    text-decoration-color: #f87171;
}

.grammar-block__line--right .grammar-block__text {
    color: #065f46;
    font-weight: 600;
}

.grammar-block__arrow {
    text-align: center;
    font-size: 0.75rem;
    color: #a8a29e;
    line-height: 1;
}

.grammar-block__hint {
    margin-top: 0.625rem;
    padding-top: 0.625rem;
    border-top: 1px dashed #e7e5e4;
    font-size: 0.75rem;
    line-height: 1.55;
    color: #57534e;
}
</style>
