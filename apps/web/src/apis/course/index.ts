import { serverApi, type Response } from '..';
import type { BatchStatusResponse, CourseList, CourseListPage } from '@en/common/course';

export const getCourseList = () => serverApi.get('/course/list') as Promise<Response<CourseListPage>>;

export const getMyCourse = () => serverApi.get('/course/my') as Promise<Response<CourseList>>;

export const getCourseBatchStatus = (ids: string[]) =>
    serverApi.get('/course/batch-status', {
        params: { ids: ids.join(',') },
    }) as Promise<Response<BatchStatusResponse>>;