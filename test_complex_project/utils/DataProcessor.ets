/**
 * 数据处理工具类 - 复杂逻辑测试
 * 包含数据转换、过滤、排序等复杂操作
 */

import { Logger } from './Logger';

// 数据验证规则
interface ValidationRule<T> {
  field: keyof T;
  required?: boolean;
  type?: 'string' | 'number' | 'boolean' | 'array' | 'object';
  min?: number;
  max?: number;
  pattern?: RegExp;
  custom?: (value: any) => boolean;
}

// 验证结果
interface ValidationResult<T> {
  valid: boolean;
  errors: { field: keyof T; message: string }[];
}

// 排序选项
interface SortOptions<T> {
  field: keyof T;
  order?: 'asc' | 'desc';
  compare?: (a: T, b: T) => number;
}

class DataProcessor {
  // 数组处理方法
  filter<T>(array: T[], predicate: (item: T, index: number) => boolean): T[] {
    return array.filter(predicate);
  }

  map<T, R>(array: T[], transformer: (item: T, index: number) => R): R[] {
    return array.map(transformer);
  }

  reduce<T, R>(array: T[], reducer: (acc: R, item: T, index: number) => R, initial: R): R {
    return array.reduce(reducer, initial);
  }

  // 链式操作支持
  chain<T>(array: T[]): DataProcessorChain<T> {
    return new DataProcessorChain<T>(array);
  }

  // 排序
  sort<T>(array: T[], options: SortOptions<T> | SortOptions<T>[]): T[] {
    const sorted = [...array];
    const optionsArray = Array.isArray(options) ? options : [options];

    sorted.sort((a, b) => {
      for (const opt of optionsArray) {
        const comparison = this.compareValues(a[opt.field], b[opt.field], opt);
        if (comparison !== 0) return comparison;
      }
      return 0;
    });

    return sorted;
  }

  private compareValues<T>(a: any, b: any, options: SortOptions<T>): number {
    if (options.compare) {
      return options.compare(a, b);
    }

    let result: number;
    if (a < b) result = -1;
    else if (a > b) result = 1;
    else result = 0;

    return options.order === 'desc' ? -result : result;
  }

  // 分组
  groupBy<T, K extends keyof T>(array: T[], key: K): Map<T[K], T[]> {
    const groups = new Map<T[K], T[]>();

    for (const item of array) {
      const groupKey = item[key];
      const group = groups.get(groupKey) || [];
      group.push(item);
      groups.set(groupKey, group);
    }

    return groups;
  }

  // 去重
  unique<T>(array: T[], key?: keyof T): T[] {
    if (!key) {
      return [...new Set(array)];
    }

    const seen = new Set<any>();
    return array.filter(item => {
      const value = item[key];
      if (seen.has(value)) return false;
      seen.add(value);
      return true;
    });
  }

  // 数据验证
  validate<T>(data: T, rules: ValidationRule<T>[]): ValidationResult<T> {
    const errors: { field: keyof T; message: string }[] = [];

    for (const rule of rules) {
      const value = data[rule.field];

      // 必填检查
      if (rule.required && (value === undefined || value === null || value === '')) {
        errors.push({ field: rule.field, message: `${String(rule.field)} is required` });
        continue;
      }

      if (value === undefined || value === null) continue;

      // 类型检查
      if (rule.type) {
        const actualType = Array.isArray(value) ? 'array' : typeof value;
        if (actualType !== rule.type) {
          errors.push({ field: rule.field, message: `${String(rule.field)} must be of type ${rule.type}` });
        }
      }

      // 数值范围检查
      if (typeof value === 'number') {
        if (rule.min !== undefined && value < rule.min) {
          errors.push({ field: rule.field, message: `${String(rule.field)} must be at least ${rule.min}` });
        }
        if (rule.max !== undefined && value > rule.max) {
          errors.push({ field: rule.field, message: `${String(rule.field)} must be at most ${rule.max}` });
        }
      }

      // 字符串长度检查
      if (typeof value === 'string') {
        if (rule.min !== undefined && value.length < rule.min) {
          errors.push({ field: rule.field, message: `${String(rule.field)} must be at least ${rule.min} characters` });
        }
        if (rule.max !== undefined && value.length > rule.max) {
          errors.push({ field: rule.field, message: `${String(rule.field)} must be at most ${rule.max} characters` });
        }
        if (rule.pattern && !rule.pattern.test(value)) {
          errors.push({ field: rule.field, message: `${String(rule.field)} format is invalid` });
        }
      }

      // 自定义验证
      if (rule.custom && !rule.custom(value)) {
        errors.push({ field: rule.field, message: `${String(rule.field)} validation failed` });
      }
    }

    return { valid: errors.length === 0, errors };
  }

  // 数据转换
  transform(input: string): string {
    return input
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_]/g, '');
  }

  parseNumber(value: string | number): number | null {
    if (typeof value === 'number') return value;
    const parsed = parseFloat(value);
    return isNaN(parsed) ? null : parsed;
  }

  parseDate(value: string | Date): Date | null {
    if (value instanceof Date) return value;
    const parsed = new Date(value);
    return isNaN(parsed.getTime()) ? null : parsed;
  }

  // 分页
  paginate<T>(array: T[], page: number, pageSize: number): { data: T[]; total: number; page: number; pageSize: number; totalPages: number } {
    const total = array.length;
    const totalPages = Math.ceil(total / pageSize);
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const data = array.slice(start, end);

    return { data, total, page, pageSize, totalPages };
  }

  // 搜索
  search<T>(array: T[], query: string, fields: (keyof T)[]): T[] {
    const lowerQuery = query.toLowerCase();
    return array.filter(item =>
      fields.some(field => {
        const value = item[field];
        if (value === null || value === undefined) return false;
        return String(value).toLowerCase().includes(lowerQuery);
      })
    );
  }

  // 深度合并
  deepMerge<T extends Record<string, any>>(target: T, source: Partial<T>): T {
    const result = { ...target };

    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.deepMerge(result[key] || {}, source[key]);
      } else {
        result[key] = source[key] as T[Extract<keyof T, string>];
      }
    }

    return result;
  }

  // 扁平化
  flatten<T>(array: (T | T[])[]): T[] {
    return array.reduce<T[]>((acc, item) => {
      if (Array.isArray(item)) {
        return acc.concat(this.flatten(item));
      }
      return acc.concat(item);
    }, []);
  }

  // 处理数组（组合操作）
  processArray<T>(array: T[]): T[] {
    return this.chain(array)
      .filter(item => item !== null && item !== undefined)
      .unique()
      .value();
  }
}

// 链式操作类
class DataProcessorChain<T> {
  private array: T[];

  constructor(array: T[]) {
    this.array = [...array];
  }

  filter(predicate: (item: T, index: number) => boolean): DataProcessorChain<T> {
    this.array = this.array.filter(predicate);
    return this;
  }

  map<R>(transformer: (item: T, index: number) => R): DataProcessorChain<R> {
    const mapped = this.array.map(transformer);
    return new DataProcessorChain<R>(mapped);
  }

  sort<K extends keyof T>(field: K, order: 'asc' | 'desc' = 'asc'): DataProcessorChain<T> {
    this.array.sort((a, b) => {
      const comparison = a[field] < b[field] ? -1 : a[field] > b[field] ? 1 : 0;
      return order === 'desc' ? -comparison : comparison;
    });
    return this;
  }

  unique(key?: keyof T): DataProcessorChain<T> {
    if (!key) {
      this.array = [...new Set(this.array)];
    } else {
      const seen = new Set<any>();
      this.array = this.array.filter(item => {
        const value = item[key];
        if (seen.has(value)) return false;
        seen.add(value);
        return true;
      });
    }
    return this;
  }

  take(count: number): DataProcessorChain<T> {
    this.array = this.array.slice(0, count);
    return this;
  }

  skip(count: number): DataProcessorChain<T> {
    this.array = this.array.slice(count);
    return this;
  }

  value(): T[] {
    return this.array;
  }
}

// 导出
export { DataProcessor, DataProcessorChain };
export type { ValidationRule, ValidationResult, SortOptions };
