/**
 * 支付服务 - 处理支付相关业务逻辑
 */

import { Logger } from '../utils/Logger';
import { Network } from '../utils/Network';
import { Order } from '../models/Order';

// 支付方式枚举
enum PaymentMethod {
  CREDIT_CARD = 'credit_card',
  DEBIT_CARD = 'debit_card',
  PAYPAL = 'paypal',
  ALIPAY = 'alipay',
  WECHAT_PAY = 'wechat_pay'
}

// 支付状态枚举
enum PaymentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  REFUNDED = 'refunded'
}

// 支付参数
interface PaymentParams {
  orderId: string;
  amount: number;
  method: PaymentMethod;
  currency?: string;
  metadata?: Record<string, any>;
}

// 支付结果
interface PaymentResult {
  success: boolean;
  transactionId?: string;
  status: PaymentStatus;
  message?: string;
  timestamp: Date;
}

// 退款参数
interface RefundParams {
  transactionId: string;
  amount?: number;
  reason?: string;
}

// 退款结果
interface RefundResult {
  success: boolean;
  refundId?: string;
  amount: number;
  timestamp: Date;
}

class PaymentService {
  private baseUrl: string = '/api/payments';
  private processingPayments: Set<string> = new Set();

  // 处理支付
  async processPayment(params: { orderId: string; amount: number }): Promise<PaymentResult> {
    const startTime = Date.now();
    
    try {
      // 检查是否正在处理
      if (this.processingPayments.has(params.orderId)) {
        return {
          success: false,
          status: PaymentStatus.FAILED,
          message: 'Payment already in progress',
          timestamp: new Date()
        };
      }

      this.processingPayments.add(params.orderId);

      // 验证支付参数
      if (!this.validatePaymentParams(params)) {
        this.processingPayments.delete(params.orderId);
        return {
          success: false,
          status: PaymentStatus.FAILED,
          message: 'Invalid payment parameters',
          timestamp: new Date()
        };
      }

      // 调用支付API
      const response = await Network.post<{
        transactionId: string;
        status: string;
      }>(`${this.baseUrl}/process`, params);

      this.processingPayments.delete(params.orderId);

      if (response.ok && response.data) {
        Logger.info('PaymentService', 'Payment processed successfully', {
          orderId: params.orderId,
          transactionId: response.data.transactionId,
          duration: Date.now() - startTime
        });

        return {
          success: true,
          transactionId: response.data.transactionId,
          status: PaymentStatus.COMPLETED,
          timestamp: new Date()
        };
      }

      return {
        success: false,
        status: PaymentStatus.FAILED,
        message: 'Payment processing failed',
        timestamp: new Date()
      };
    } catch (error) {
      this.processingPayments.delete(params.orderId);
      Logger.error('PaymentService', 'Payment processing error', error);
      
      return {
        success: false,
        status: PaymentStatus.FAILED,
        message: 'Network error during payment',
        timestamp: new Date()
      };
    }
  }

  // 验证支付
  async verifyPayment(transactionId: string): Promise<PaymentResult> {
    try {
      const response = await Network.get<{
        status: string;
        amount: number;
      }>(`${this.baseUrl}/verify/${transactionId}`);

      if (response.ok && response.data) {
        return {
          success: response.data.status === 'completed',
          transactionId,
          status: this.parsePaymentStatus(response.data.status),
          timestamp: new Date()
        };
      }

      return {
        success: false,
        transactionId,
        status: PaymentStatus.FAILED,
        message: 'Verification failed',
        timestamp: new Date()
      };
    } catch (error) {
      Logger.error('PaymentService', 'Payment verification error', error);
      return {
        success: false,
        transactionId,
        status: PaymentStatus.FAILED,
        message: 'Verification error',
        timestamp: new Date()
      };
    }
  }

  // 处理退款
  async processRefund(params: RefundParams): Promise<RefundResult> {
    try {
      const response = await Network.post<{
        refundId: string;
        amount: number;
      }>(`${this.baseUrl}/refund`, params);

      if (response.ok && response.data) {
        Logger.info('PaymentService', 'Refund processed', {
          transactionId: params.transactionId,
          refundId: response.data.refundId
        });

        return {
          success: true,
          refundId: response.data.refundId,
          amount: response.data.amount,
          timestamp: new Date()
        };
      }

      return {
        success: false,
        amount: params.amount || 0,
        timestamp: new Date()
      };
    } catch (error) {
      Logger.error('PaymentService', 'Refund processing error', error);
      return {
        success: false,
        amount: params.amount || 0,
        timestamp: new Date()
      };
    }
  }

  // 获取支付方式
  getPaymentMethods(): PaymentMethod[] {
    return Object.values(PaymentMethod);
  }

  // 获取支付方式显示名称
  getPaymentMethodName(method: PaymentMethod): string {
    const names: Record<PaymentMethod, string> = {
      [PaymentMethod.CREDIT_CARD]: 'Credit Card',
      [PaymentMethod.DEBIT_CARD]: 'Debit Card',
      [PaymentMethod.PAYPAL]: 'PayPal',
      [PaymentMethod.ALIPAY]: 'Alipay',
      [PaymentMethod.WECHAT_PAY]: 'WeChat Pay'
    };
    return names[method] || method;
  }

  // 格式化金额
  formatAmount(amount: number, currency: string = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency
    }).format(amount);
  }

  // 计算手续费
  calculateFee(amount: number, method: PaymentMethod): number {
    const fees: Record<PaymentMethod, number> = {
      [PaymentMethod.CREDIT_CARD]: 0.029,
      [PaymentMethod.DEBIT_CARD]: 0.025,
      [PaymentMethod.PAYPAL]: 0.034,
      [PaymentMethod.ALIPAY]: 0.025,
      [PaymentMethod.WECHAT_PAY]: 0.025
    };
    
    const rate = fees[method] || 0.03;
    return amount * rate;
  }

  // 验证支付参数
  private validatePaymentParams(params: { orderId: string; amount: number }): boolean {
    if (!params.orderId || params.orderId.trim() === '') {
      return false;
    }
    if (params.amount <= 0) {
      return false;
    }
    return true;
  }

  // 解析支付状态
  private parsePaymentStatus(status: string): PaymentStatus {
    const statusMap: Record<string, PaymentStatus> = {
      'pending': PaymentStatus.PENDING,
      'processing': PaymentStatus.PROCESSING,
      'completed': PaymentStatus.COMPLETED,
      'failed': PaymentStatus.FAILED,
      'refunded': PaymentStatus.REFUNDED
    };
    return statusMap[status] || PaymentStatus.FAILED;
  }

  // 检查支付是否可退款
  isRefundable(payment: PaymentResult): boolean {
    return payment.status === PaymentStatus.COMPLETED;
  }

  // 获取支付历史
  async getPaymentHistory(orderId: string): Promise<PaymentResult[]> {
    try {
      const response = await Network.get<PaymentResult[]>(`${this.baseUrl}/history/${orderId}`);
      
      if (response.ok && response.data) {
        return response.data;
      }
      
      return [];
    } catch (error) {
      Logger.error('PaymentService', 'Failed to get payment history', error);
      return [];
    }
  }
}

export { PaymentService, PaymentMethod, PaymentStatus };
export type { PaymentParams, PaymentResult, RefundParams, RefundResult };
