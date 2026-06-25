import { useRouter } from 'vue-router';
import type { Course, CourseBatchStatus } from '@en/common/course';

export function useCourseAction() {
    const router = useRouter();

    const toCourse = (item: CourseBatchStatus): Course => ({
        id: item.id,
        name: item.name,
        value: item.value,
        description: item.description,
        teacher: item.teacher,
        url: item.url,
        price: item.price,
    });

    const goLearn = (course: Course | CourseBatchStatus) => {
        const c = 'purchased' in course ? toCourse(course) : course;
        router.push(`/courses/learn/${c.id}/${encodeURIComponent(c.name)}`);
    };

    return { goLearn, toCourse };
}
