/**
 * 辅助函数工具类 - 箭头函数测试
 * 包含各种实用工具函数
 */

import { Logger } from './Logger';

// 防抖函数
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: number | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => {
      func(...args);
    }, wait) as unknown as number;
  };
};

// 节流函数
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle = false;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
};

// 记忆化函数
export const memoize = <T extends (...args: any[]) => any>(func: T): T => {
  const cache = new Map<string, ReturnType<T>>();

  return ((...args: Parameters<T>): ReturnType<T> => {
    const key = JSON.stringify(args);
    if (cache.has(key)) {
      return cache.get(key)!;
    }
    const result = func(...args);
    cache.set(key, result);
    return result;
  }) as T;
};

// 柯里化函数
export const curry = <T extends (...args: any[]) => any>(func: T) => {
  return function curried(...args: any[]): any {
    if (args.length >= func.length) {
      return func(...args);
    } else {
      return (...nextArgs: any[]) => curried(...args, ...nextArgs);
    }
  };
};

// 组合函数
export const compose = <R>(...fns: Array<(a: any) => any>) => {
  return (x: any): R => fns.reduceRight((acc, fn) => fn(acc), x);
};

// 管道函数
export const pipe = <R>(...fns: Array<(a: any) => any>) => {
  return (x: any): R => fns.reduce((acc, fn) => fn(acc), x);
};

// 辅助类
class Helper {
  // 生成唯一ID
  generateId = (): string => {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  // 格式化文件大小
  formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  // 格式化时间
  formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
    return `${(ms / 3600000).toFixed(1)}h`;
  };

  // 检查条件
  checkCondition = (): boolean => {
    return Math.random() > 0.5;
  };

  // 延迟执行
  delay = (ms: number): Promise<void> => {
    return new Promise(resolve => setTimeout(resolve, ms));
  };

  // 重试函数
  retry = async <T>(
    fn: () => Promise<T>,
    maxAttempts: number = 3,
    delay: number = 1000
  ): Promise<T> => {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;
        Logger.warn('Helper', `Retry attempt ${attempt}/${maxAttempts} failed`);
        
        if (attempt < maxAttempts) {
          await this.delay(delay);
        }
      }
    }

    throw lastError;
  };

  // 深拷贝
  deepClone = <T>(obj: T): T => {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T;
    if (Array.isArray(obj)) return obj.map(item => this.deepClone(item)) as unknown as T;
    
    const cloned = {} as T;
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        cloned[key] = this.deepClone(obj[key]);
      }
    }
    return cloned;
  };

  // 对象路径获取
  getPath = (obj: any, path: string, defaultValue?: any): any => {
    const keys = path.split('.');
    let result = obj;

    for (const key of keys) {
      if (result === null || result === undefined) return defaultValue;
      result = result[key];
    }

    return result !== undefined ? result : defaultValue;
  };

  // 对象路径设置
  setPath = (obj: any, path: string, value: any): void => {
    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in current) || typeof current[key] !== 'object') {
        current[key] = {};
      }
      current = current[key];
    }

    current[keys[keys.length - 1]] = value;
  };

  // 随机生成
  randomInt = (min: number, max: number): number => {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  };

  randomChoice = <T>(array: T[]): T => {
    return array[Math.floor(Math.random() * array.length)];
  };

  shuffle = <T>(array: T[]): T[] => {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  };

  // 字符串工具
  camelCase = (str: string): string => {
    return str
      .replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) =>
        index === 0 ? word.toLowerCase() : word.toUpperCase()
      )
      .replace(/\s+/g, '');
  };

  kebabCase = (str: string): string => {
    return str
      .replace(/([a-z])([A-Z])/g, '$1-$2')
      .replace(/[\s_]+/g, '-')
      .toLowerCase();
  };

  snakeCase = (str: string): string => {
    return str
      .replace(/([a-z])([A-Z])/g, '$1_$2')
      .replace(/[\s-]+/g, '_')
      .toLowerCase();
  };

  truncate = (str: string, maxLength: number, suffix: string = '...'): string => {
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength - suffix.length) + suffix;
  };

  // 数组分块
  chunk = <T>(array: T[], size: number): T[][] => {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  };

  // 数组交集
  intersection = <T>(array1: T[], array2: T[]): T[] => {
    const set = new Set(array2);
    return array1.filter(item => set.has(item));
  };

  // 数组差集
  difference = <T>(array1: T[], array2: T[]): T[] => {
    const set = new Set(array2);
    return array1.filter(item => !set.has(item));
  };

  // 数组并集
  union = <T>(array1: T[], array2: T[]): T[] => {
    return [...new Set([...array1, ...array2])];
  };
}

// 导出
export { Helper };
