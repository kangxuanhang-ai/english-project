import { aiApi, type Response } from '..';

export interface CourseRecommendation {
    course_id: string | null;
    title: string;
    reason: string;
    match_score: number;
}

export interface DailyPlan {
    new_words_per_day: number;
    review_frequency: string;
    estimated_completion: string;
}

export interface RecommendData {
    courses: CourseRecommendation[];
    daily_plan: DailyPlan;
    summary: string;
    cached: boolean;
    generated_at: string | null;
}

export const getRecommend = (force = false) =>
    aiApi.get('/recommend', { params: { force } }) as Promise<Response<RecommendData>>;

/** 清除 AI 推荐缓存（打卡/学词/购课后调用） */
export const clearRecommendCache = () =>
    aiApi.post('/recommend/cache/clear') as Promise<Response<null>>;
