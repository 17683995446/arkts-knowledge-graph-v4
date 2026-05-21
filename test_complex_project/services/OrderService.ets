/**
 * 订单服务 - 处理订单相关业务逻辑
 */

import { Logger } from '../utils/Logger';
import { Network } from '../utils/Network';
import { Order } from '../models/Order';
import { User } from '../models/User';

// 订单创建参数
interface CreateOrderParams {
  userId: string;
  productId: string;
  quantity: number;
  address?: string;
  notes?: string;
}

// 订单查询参数
interface OrderQueryParams {
  userId?: string;
  status?: string;
  startDate?: Date;
  endDate?: Date;
  page?: number;
  pageSize?: number;
}

// 订单统计
interface OrderStatistics {
  totalOrders: number;
  totalAmount: number;
  averageAmount: number;
  pendingOrders: number;
  completedOrders: number;
}

class OrderService {
  private baseUrl: string = '/api/orders';

  // 获取订单列表
  async getOrders(params: OrderQueryParams = {}): Promise<Order[]> {
    try {
      const queryString = Network.buildQueryString(params);
      const response = await Network.get<Order[]>(`${this.baseUrl}${queryString}`);
      
      if (response.ok && response.data) {
        return response.data;
      }
      
      return [];
    } catch (error) {
      Logger.error('OrderService', 'Failed to get orders', error);
      return [];
    }
  }

  // 根据用户ID获取订单
  async getOrdersByUserId(userId: string): Promise<{ success: boolean; data?: Order[]; error?: string }> {
    try {
      const response = await Network.get<Order[]>(`${this.baseUrl}?userId=${userId}`);
      
      if (response.ok && response.data) {
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'Failed to fetch orders' };
    } catch (error) {
      Logger.error('OrderService', 'Failed to get orders by user', error);
      return { success: false, error: 'Network error' };
    }
  }

  // 获取单个订单
  async getOrderById(orderId: string): Promise<Order | null> {
    try {
      const response = await Network.get<Order>(`${this.baseUrl}/${orderId}`);
      
      if (response.ok && response.data) {
        return response.data;
      }
      
      return null;
    } catch (error) {
      Logger.error('OrderService', 'Failed to get order', error);
      return null;
    }
  }

  // 创建订单
  async createOrder(params: CreateOrderParams): Promise<Order | null> {
    try {
      // 验证参数
      if (!this.validateOrderParams(params)) {
        Logger.warn('OrderService', 'Invalid order parameters');
        return null;
      }

      const response = await Network.post<Order>(this.baseUrl, params);
      
      if (response.ok && response.data) {
        Logger.info('OrderService', 'Order created', { orderId: response.data.id });
        return response.data;
      }
      
      return null;
    } catch (error) {
      Logger.error('OrderService', 'Failed to create order', error);
      return null;
    }
  }

  // 更新订单
  async updateOrder(orderId: string, updates: Partial<Order>): Promise<Order | null> {
    try {
      const response = await Network.put<Order>(`${this.baseUrl}/${orderId}`, updates);
      
      if (response.ok && response.data) {
        return response.data;
      }
      
      return null;
    } catch (error) {
      Logger.error('OrderService', 'Failed to update order', error);
      return null;
    }
  }

  // 取消订单
  async cancelOrder(orderId: string): Promise<boolean> {
    try {
      const response = await Network.patch(`${this.baseUrl}/${orderId}`, { status: 'cancelled' });
      return response.ok;
    } catch (error) {
      Logger.error('OrderService', 'Failed to cancel order', error);
      return false;
    }
  }

  // 完成订单
  async completeOrder(orderId: string): Promise<boolean> {
    try {
      const response = await Network.patch(`${this.baseUrl}/${orderId}`, { status: 'completed' });
      return response.ok;
    } catch (error) {
      Logger.error('OrderService', 'Failed to complete order', error);
      return false;
    }
  }

  // 删除订单
  async deleteOrder(orderId: string): Promise<boolean> {
    try {
      const response = await Network.delete(`${this.baseUrl}/${orderId}`);
      return response.ok;
    } catch (error) {
      Logger.error('OrderService', 'Failed to delete order', error);
      return false;
    }
  }

  // 计算订单总额
  calculateTotal(items: { price: number; quantity: number }[]): number {
    return items.reduce((total, item) => total + item.price * item.quantity, 0);
  }

  // 应用折扣
  applyDiscount(total: number, discountPercent: number): number {
    return total * (1 - discountPercent / 100);
  }

  // 计算税费
  calculateTax(amount: number, taxRate: number): number {
    return amount * (taxRate / 100);
  }

  // 计算最终金额
  calculateFinalAmount(subtotal: number, discount: number, tax: number, shipping: number): number {
    const afterDiscount = this.applyDiscount(subtotal, discount);
    const taxAmount = this.calculateTax(afterDiscount, tax);
    return afterDiscount + taxAmount + shipping;
  }

  // 验证订单参数
  private validateOrderParams(params: CreateOrderParams): boolean {
    if (!params.userId || !params.productId) return false;
    if (!params.quantity || params.quantity <= 0) return false;
    return true;
  }

  // 获取订单统计
  async getStatistics(userId?: string): Promise<OrderStatistics> {
    try {
      const orders = await this.getOrders({ userId });
      
      const totalOrders = orders.length;
      const totalAmount = orders.reduce((sum, order) => sum + order.totalAmount, 0);
      const pendingOrders = orders.filter(o => o.status === 'pending').length;
      const completedOrders = orders.filter(o => o.status === 'completed').length;
      
      return {
        totalOrders,
        totalAmount,
        averageAmount: totalOrders > 0 ? totalAmount / totalOrders : 0,
        pendingOrders,
        completedOrders
      };
    } catch (error) {
      Logger.error('OrderService', 'Failed to get statistics', error);
      return {
        totalOrders: 0,
        totalAmount: 0,
        averageAmount: 0,
        pendingOrders: 0,
        completedOrders: 0
      };
    }
  }

  // 批量更新订单状态
  async batchUpdateStatus(orderIds: string[], status: string): Promise<{ success: string[]; failed: string[] }> {
    const success: string[] = [];
    const failed: string[] = [];

    for (const orderId of orderIds) {
      try {
        const response = await Network.patch(`${this.baseUrl}/${orderId}`, { status });
        if (response.ok) {
          success.push(orderId);
        } else {
          failed.push(orderId);
        }
      } catch {
        failed.push(orderId);
      }
    }

    return { success, failed };
  }
}

export { OrderService };
export type { CreateOrderParams, OrderQueryParams, OrderStatistics };
