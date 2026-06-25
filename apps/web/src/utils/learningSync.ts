import { clearRecommendCache } from '@/apis/recommend';
import { ElMessage } from 'element-plus';

/** 学习行为变更后同步 AI 侧（清推荐缓存） */
export async function syncLearningToAi() {
    try {
        await clearRecommendCache();
    } catch {
        ElMessage.warning('学习数据同步失败，推荐可能不是最新');
    }
}
