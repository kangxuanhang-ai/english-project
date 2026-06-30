import 'dotenv/config';
import { PrismaClient } from '../libs/shared/src/generated/prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';
import * as fs from 'fs';
import * as readline from 'readline';
import * as iconv from 'iconv-lite';

const adapter = new PrismaPg({
  connectionString:
    process.env.DATABASE_URL ||
    'postgres://postgres:123456@localhost:5432/english',
});
const prisma = new PrismaClient({ adapter });

// 解析 CSV 一行（处理引号内的逗号）
function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

// 解析 tag 字段为布尔值
function parseTagToBoolean(tagValue: string) {
  const tags = tagValue
    ? tagValue.split(' ').filter((t) => t.trim() !== '')
    : [];
  return {
    zk: tags.includes('zk'),
    gk: tags.includes('gk'),
    cet4: tags.includes('cet4'),
    cet6: tags.includes('cet6'),
    ky: tags.includes('ky'),
    toefl: tags.includes('toefl'),
    ielts: tags.includes('ielts'),
    gre: tags.includes('gre'),
  };
}

async function readLargeCSV(filePath: string) {
  let lineCount = 0;
  let headers: string[] = [];
  let batch: any[] = [];
  const BATCH_SIZE = 2000;
  let totalInserted = 0;

  console.log('开始读取 CSV 文件并插入数据库...\n');

  const fileStream = fs
    .createReadStream(filePath)
    .pipe(iconv.decodeStream('gbk'));
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    lineCount++;
    if (lineCount === 1) {
      headers = line.split(',');
      continue;
    }

    const values = parseCSVLine(line);
    const rowData: Record<string, string> = {};
    headers.forEach((header, index) => {
      rowData[header] = values[index] || '';
    });

    const booleanFields = parseTagToBoolean(rowData.tag);

    const wordData = {
      word: rowData.word || '',
      phonetic: rowData.phonetic || null,
      definition: rowData.definition || null,
      translation: rowData.translation || null,
      pos: rowData.pos || null,
      collins: rowData.collins || null,
      oxford: rowData.oxford || null,
      tag: rowData.tag || null,
      bnc: rowData.bnc || null,
      frq: rowData.frq || null,
      exchange: rowData.exchange || null,
      ...booleanFields,
    };

    batch.push(wordData);

    if (batch.length >= BATCH_SIZE) {
      await prisma.wordBook.createMany({ data: batch, skipDuplicates: true });
      totalInserted += batch.length;
      console.log(`已插入 ${totalInserted.toLocaleString()} 条数据...`);
      batch = [];
    }
  }

  if (batch.length > 0) {
    await prisma.wordBook.createMany({ data: batch, skipDuplicates: true });
    totalInserted += batch.length;
  }

  console.log(`插入完成！共插入 ${totalInserted.toLocaleString()} 条数据`);
  await prisma.$disconnect();
}

readLargeCSV('prisma/ecdict.csv').catch(console.error);
