import { serverApi, type Response } from '..';
import type { ResultLearn } from '@en/common/learn';
import type { Word } from '@en/common/word';
export const getWordList = (courseId: string) => serverApi.get(`/learn/word/${courseId}`) as Promise<Response<Word[]>>;
export const saveWordMaster = (wordIds: string[]) => serverApi.post(`/learn/word/master`, { wordIds }) as Promise<Response<ResultLearn>>;