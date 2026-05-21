/**
 * 网络工具类 - 异步方法测试
 * 包含HTTP请求、重试机制、缓存等
 */

import { Logger } from './Logger';

// HTTP方法枚举
enum HttpMethod {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  DELETE = 'DELETE',
  PATCH = 'PATCH'
}

// 请求配置接口
interface RequestConfig {
  method?: HttpMethod;
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  cache?: boolean;
}

// 响应接口
interface HttpResponse<T = any> {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: T;
  ok: boolean;
}

// 网络错误类
class NetworkError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message);
    this.name = 'NetworkError';
  }
}

class Network {
  // 默认配置
  private static defaultConfig: RequestConfig = {
    method: HttpMethod.GET,
    timeout: 30000,
    retries: 3,
    retryDelay: 1000,
    cache: false
  };

  // 缓存存储
  private static cache: Map<string, { data: any; timestamp: number }> = new Map();
  private static cacheDuration: number = 5 * 60 * 1000; // 5分钟

  // 设置默认配置
  static setDefaultConfig(config: Partial<RequestConfig>): void {
    Network.defaultConfig = { ...Network.defaultConfig, ...config };
  }

  // 核心请求方法
  static async request<T = any>(url: string, config: RequestConfig = {}): Promise<HttpResponse<T>> {
    const mergedConfig = { ...Network.defaultConfig, ...config };

    // 检查缓存
    if (mergedConfig.cache && mergedConfig.method === HttpMethod.GET) {
      const cached = Network.getFromCache(url);
      if (cached) {
        Logger.debug('Network', 'Cache hit', { url });
        return cached;
      }
    }

    // 执行请求（带重试）
    return Network.executeWithRetry(url, mergedConfig);
  }

  // 带重试的请求执行
  private static async executeWithRetry<T>(
    url: string,
    config: RequestConfig
  ): Promise<HttpResponse<T>> {
    const maxRetries = config.retries || 0;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await Network.executeRequest<T>(url, config);
        
        // 缓存响应
        if (config.cache && config.method === HttpMethod.GET) {
          Network.setCache(url, response);
        }

        return response;
      } catch (error) {
        lastError = error as Error;
        Logger.warn('Network', `Request failed (attempt ${attempt + 1}/${maxRetries + 1})`, { url, error });

        if (attempt < maxRetries) {
          await Network.delay(config.retryDelay || 1000);
        }
      }
    }

    throw lastError || new NetworkError('Request failed after retries');
  }

  // 执行单个请求
  private static async executeRequest<T>(url: string, config: RequestConfig): Promise<HttpResponse<T>> {
    return new Promise((resolve, reject) => {
      // 模拟HTTP请求
      setTimeout(() => {
        const mockResponse: HttpResponse<T> = {
          status: 200,
          statusText: 'OK',
          headers: { 'Content-Type': 'application/json' },
          data: {} as T,
          ok: true
        };
        resolve(mockResponse);
      }, 100);
    });
  }

  // 便捷方法
  static async get<T>(url: string, config?: RequestConfig): Promise<HttpResponse<T>> {
    return Network.request<T>(url, { ...config, method: HttpMethod.GET });
  }

  static async post<T>(url: string, body?: any, config?: RequestConfig): Promise<HttpResponse<T>> {
    return Network.request<T>(url, { ...config, method: HttpMethod.POST, body });
  }

  static async put<T>(url: string, body?: any, config?: RequestConfig): Promise<HttpResponse<T>> {
    return Network.request<T>(url, { ...config, method: HttpMethod.PUT, body });
  }

  static async delete<T>(url: string, config?: RequestConfig): Promise<HttpResponse<T>> {
    return Network.request<T>(url, { ...config, method: HttpMethod.DELETE });
  }

  static async patch<T>(url: string, body?: any, config?: RequestConfig): Promise<HttpResponse<T>> {
    return Network.request<T>(url, { ...config, method: HttpMethod.PATCH, body });
  }

  // 缓存管理
  private static getFromCache<T>(key: string): HttpResponse<T> | null {
    const cached = Network.cache.get(key);
    if (!cached) return null;

    const now = Date.now();
    if (now - cached.timestamp > Network.cacheDuration) {
      Network.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  private static setCache(key: string, data: any): void {
    Network.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  static clearCache(): void {
    Network.cache.clear();
  }

  // 工具方法
  private static delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  static buildQueryString(params: Record<string, any>): string {
    const query = Object.entries(params)
      .filter(([, value]) => value !== undefined && value !== null)
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
      .join('&');
    return query ? `?${query}` : '';
  }

  static parseQueryString(query: string): Record<string, string> {
    const params: Record<string, string> = {};
    const searchParams = new URLSearchParams(query);
    searchParams.forEach((value, key) => {
      params[key] = value;
    });
    return params;
  }

  // 批量请求
  static async all<T>(requests: Promise<HttpResponse<T>>[]): Promise<HttpResponse<T>[]> {
    return Promise.all(requests);
  }

  static async race<T>(requests: Promise<HttpResponse<T>>[]): Promise<HttpResponse<T>> {
    return Promise.race(requests);
  }
}

// 导出
export { Network, HttpMethod, NetworkError };
export type { RequestConfig, HttpResponse };
