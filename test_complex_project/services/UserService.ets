/**
 * 用户服务 - 处理用户相关业务逻辑
 */

import { Logger } from '../utils/Logger';
import { Network } from '../utils/Network';
import { User } from '../models/User';

// 服务响应接口
interface ServiceResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// 用户查询参数
interface UserQueryParams {
  page?: number;
  pageSize?: number;
  search?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

class UserService {
  private baseUrl: string = '/api/users';
  private cache: Map<string, User> = new Map();

  // 获取单个用户
  async getUserById(id: string): Promise<ServiceResponse<User>> {
    try {
      // 检查缓存
      const cached = this.cache.get(id);
      if (cached) {
        Logger.info('UserService', 'Cache hit for user', { id });
        return { success: true, data: cached };
      }

      const response = await Network.get<User>(`${this.baseUrl}/${id}`);
      
      if (response.ok && response.data) {
        // 缓存结果
        this.cache.set(id, response.data);
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'User not found' };
    } catch (error) {
      Logger.error('UserService', 'Failed to get user', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 获取用户列表
  async getUsers(params: UserQueryParams = {}): Promise<ServiceResponse<User[]>> {
    try {
      const queryString = Network.buildQueryString(params);
      const response = await Network.get<User[]>(`${this.baseUrl}${queryString}`);
      
      if (response.ok && response.data) {
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'Failed to fetch users' };
    } catch (error) {
      Logger.error('UserService', 'Failed to get users', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 创建用户
  async createUser(userData: Partial<User>): Promise<ServiceResponse<User>> {
    try {
      const response = await Network.post<User>(this.baseUrl, userData);
      
      if (response.ok && response.data) {
        // 更新缓存
        this.cache.set(response.data.id, response.data);
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'Failed to create user' };
    } catch (error) {
      Logger.error('UserService', 'Failed to create user', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 更新用户
  async updateUser(id: string, userData: Partial<User>): Promise<ServiceResponse<User>> {
    try {
      const response = await Network.put<User>(`${this.baseUrl}/${id}`, userData);
      
      if (response.ok && response.data) {
        // 更新缓存
        this.cache.set(id, response.data);
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'Failed to update user' };
    } catch (error) {
      Logger.error('UserService', 'Failed to update user', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 删除用户
  async deleteUser(id: string): Promise<ServiceResponse<void>> {
    try {
      const response = await Network.delete(`${this.baseUrl}/${id}`);
      
      if (response.ok) {
        // 从缓存移除
        this.cache.delete(id);
        return { success: true };
      }
      
      return { success: false, error: 'Failed to delete user' };
    } catch (error) {
      Logger.error('UserService', 'Failed to delete user', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 用户登录
  async login(email: string, password: string): Promise<ServiceResponse<{ user: User; token: string }>> {
    try {
      const response = await Network.post<{ user: User; token: string }>(`${this.baseUrl}/login`, {
        email,
        password
      });
      
      if (response.ok && response.data) {
        // 缓存用户信息
        this.cache.set(response.data.user.id, response.data.user);
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'Invalid credentials' };
    } catch (error) {
      Logger.error('UserService', 'Login failed', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 用户登出
  async logout(): Promise<ServiceResponse<void>> {
    try {
      await Network.post(`${this.baseUrl}/logout`);
      this.clearCache();
      return { success: true };
    } catch (error) {
      Logger.error('UserService', 'Logout failed', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 验证用户权限
  hasPermission(user: User, permission: string): boolean {
    return user.permissions?.includes(permission) || false;
  }

  // 检查用户角色
  hasRole(user: User, role: string): boolean {
    return user.role === role;
  }

  // 获取用户全名
  getFullName(user: User): string {
    return `${user.firstName || ''} ${user.lastName || ''}`.trim();
  }

  // 清除缓存
  clearCache(): void {
    this.cache.clear();
  }
}

export { UserService };
export type { ServiceResponse, UserQueryParams };
