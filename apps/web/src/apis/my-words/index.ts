import { serverApi, type Response } from '..';
import type { AddWordsDto, MarkMasteredDto, MyWordList } from '@en/common/word';

export const getMyWords = (params: {
    status: 'learning' | 'mastered';
    page: number;
    pageSize: number;
}): Promise<Response<MyWordList>> => {
    return serverApi.get('/my-words', { params }) as Promise<Response<MyWordList>>;
};

export const addMyWords = (data: AddWordsDto): Promise<Response<{ added: string[]; skipped: string[] }>> => {
    return serverApi.post('/my-words', data) as Promise<Response<{ added: string[]; skipped: string[] }>>;
};

export const markMyWordsMastered = (
    data: MarkMasteredDto
): Promise<Response<{ wordNumber: number; newlyMastered: number }>> => {
    return serverApi.post('/my-words/master', data) as Promise<
        Response<{ wordNumber: number; newlyMastered: number }>
    >;
};

export const removeMyWord = (wordId: string): Promise<Response<{ removed: boolean }>> => {
    return serverApi.delete(`/my-words/${wordId}`) as Promise<Response<{ removed: boolean }>>;
};
