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
