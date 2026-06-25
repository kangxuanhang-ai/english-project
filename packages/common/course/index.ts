//定义单个课程的接口
export interface Course {
    id: string; // 课程ID
    name: string; // 课程名
    value: string; // 课程标识 gk
    description?: string; // 课程描述
    teacher: string; // 教师
    url: string; // 课程url
    price: string; // 课程价格
}
//定义多个课程的列表
export type CourseList = Course[];

export interface CourseListPage {
    list: CourseList;
    total: number;
}

export interface CourseBatchStatus extends Course {
    purchased: boolean;
}

export interface BatchStatusResponse {
    items: CourseBatchStatus[];
    missingIds: string[];
}