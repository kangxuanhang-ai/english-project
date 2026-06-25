import { serverApi, type Response } from '..';
import type { CreatePayDto, ResultPay, SyncPayDto, SyncPayResult, ResumePayDto } from '@en/common/pay';

export const createPay = (data: CreatePayDto) => serverApi.post('/pay/create', data) as Promise<Response<ResultPay>>;

export const syncPay = (data: SyncPayDto) => serverApi.post('/pay/sync', data) as Promise<Response<SyncPayResult>>;

export const resumePay = (data: ResumePayDto) => serverApi.post('/pay/resume', data) as Promise<Response<ResultPay>>;