/**
 * 用户服务类
 * 处理用户相关的API请求
 */
import { Logger } from './Logger';

export class UserService {
  private baseUrl: string = 'https://api.example.com';
  private logger: Logger = new Logger('UserService');
  
  // 获取用户列表
  async fetchUsers(page: number = 1, pageSize: number = 10): Promise<User[]> {
    this.logger.debug(`Fetching users, page: ${page}`);
    
    try {
      const response = await fetch(`${this.baseUrl}/users?page=${page}&size=${pageSize}`);
      const data = await response.json();
      return data.users as User[];
    } catch (error) {
      this.logger.error('Failed to fetch users', error);
      throw error;
    }
  }
  
  // 根据ID获取用户
  async getUserById(id: number): Promise<User> {
    this.logger.debug(`Fetching user by id: ${id}`);
    
    const response = await fetch(`${this.baseUrl}/users/${id}`);
    const data = await response.json();
    return data as User;
  }
  
  // 创建用户
  async createUser(userData: Omit<User, 'id'>): Promise<User> {
    this.logger.info('Creating new user');
    
    const response = await fetch(`${this.baseUrl}/users`, {
      method: 'POST',
      body: JSON.stringify(userData)
    });
    const data = await response.json();
    return data as User;
  }
  
  // 更新用户
  async updateUser(id: number, userData: Partial<User>): Promise<User> {
    this.logger.info(`Updating user: ${id}`);
    
    const response = await fetch(`${this.baseUrl}/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(userData)
    });
    const data = await response.json();
    return data as User;
  }
  
  // 删除用户
  async deleteUser(id: number): Promise<boolean> {
    this.logger.info(`Deleting user: ${id}`);
    
    const response = await fetch(`${this.baseUrl}/users/${id}`, {
      method: 'DELETE'
    });
    return response.ok;
  }
  
  // 搜索用户
  async searchUsers(keyword: string): Promise<User[]> {
    this.logger.debug(`Searching users with keyword: ${keyword}`);
    
    const response = await fetch(`${this.baseUrl}/users/search?q=${encodeURIComponent(keyword)}`);
    const data = await response.json();
    return data.users as User[];
  }
}

interface User {
  id: number;
  name: string;
  email: string;
  avatar?: string;
}
