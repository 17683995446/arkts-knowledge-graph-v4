/**
 * 订单模型 - 定义订单数据结构
 */

import { User } from './User';
import { Product } from './Product';

// 订单状态枚举
enum OrderStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  PROCESSING = 'processing',
  SHIPPED = 'shipped',
  DELIVERED = 'delivered',
  CANCELLED = 'cancelled',
  REFUNDED = 'refunded'
}

// 订单项
interface OrderItem {
  id: string;
  productId: string;
  product?: Product;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

// 订单地址
interface OrderAddress {
  recipientName: string;
  phone: string;
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

// 订单支付信息
interface OrderPayment {
  method: string;
  transactionId?: string;
  paidAt?: Date;
  amount: number;
}

// 订单模型
interface Order {
  id: string;
  userId: string;
  user?: User;
  items: OrderItem[];
  status: OrderStatus;
  address: OrderAddress;
  payment?: OrderPayment;
  subtotal: number;
  discount: number;
  tax: number;
  shipping: number;
  totalAmount: number;
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
  shippedAt?: Date;
  deliveredAt?: Date;
}

// 订单构建器
class OrderBuilder {
  private order: Partial<Order> = {
    items: [],
    status: OrderStatus.PENDING,
    subtotal: 0,
    discount: 0,
    tax: 0,
    shipping: 0,
    totalAmount: 0,
    createdAt: new Date(),
    updatedAt: new Date()
  };

  setId(id: string): OrderBuilder {
    this.order.id = id;
    return this;
  }

  setUserId(userId: string): OrderBuilder {
    this.order.userId = userId;
    return this;
  }

  setUser(user: User): OrderBuilder {
    this.order.user = user;
    this.order.userId = user.id;
    return this;
  }

  addItem(item: OrderItem): OrderBuilder {
    if (!this.order.items) {
      this.order.items = [];
    }
    this.order.items.push(item);
    this.recalculateTotals();
    return this;
  }

  removeItem(itemId: string): OrderBuilder {
    if (this.order.items) {
      this.order.items = this.order.items.filter(item => item.id !== itemId);
      this.recalculateTotals();
    }
    return this;
  }

  setAddress(address: OrderAddress): OrderBuilder {
    this.order.address = address;
    return this;
  }

  setPayment(payment: OrderPayment): OrderBuilder {
    this.order.payment = payment;
    return this;
  }

  setDiscount(discount: number): OrderBuilder {
    this.order.discount = discount;
    this.recalculateTotals();
    return this;
  }

  setTax(tax: number): OrderBuilder {
    this.order.tax = tax;
    this.recalculateTotals();
    return this;
  }

  setShipping(shipping: number): OrderBuilder {
    this.order.shipping = shipping;
    this.recalculateTotals();
    return this;
  }

  setNotes(notes: string): OrderBuilder {
    this.order.notes = notes;
    return this;
  }

  setStatus(status: OrderStatus): OrderBuilder {
    this.order.status = status;
    this.order.updatedAt = new Date();
    
    if (status === OrderStatus.SHIPPED) {
      this.order.shippedAt = new Date();
    } else if (status === OrderStatus.DELIVERED) {
      this.order.deliveredAt = new Date();
    }
    
    return this;
  }

  private recalculateTotals(): void {
    const items = this.order.items || [];
    const subtotal = items.reduce((sum, item) => sum + item.totalPrice, 0);
    const discount = this.order.discount || 0;
    const tax = this.order.tax || 0;
    const shipping = this.order.shipping || 0;
    
    this.order.subtotal = subtotal;
    this.order.totalAmount = subtotal - discount + tax + shipping;
  }

  build(): Order {
    if (!this.order.id || !this.order.userId) {
      throw new Error('Order must have id and userId');
    }
    if (!this.order.items || this.order.items.length === 0) {
      throw new Error('Order must have at least one item');
    }
    if (!this.order.address) {
      throw new Error('Order must have an address');
    }
    
    return this.order as Order;
  }
}

// 订单项构建器
class OrderItemBuilder {
  private item: Partial<OrderItem> = {
    quantity: 1,
    totalPrice: 0
  };

  setId(id: string): OrderItemBuilder {
    this.item.id = id;
    return this;
  }

  setProductId(productId: string): OrderItemBuilder {
    this.item.productId = productId;
    return this;
  }

  setProduct(product: Product): OrderItemBuilder {
    this.item.product = product;
    this.item.productId = product.id;
    this.item.unitPrice = product.price;
    this.recalculateTotal();
    return this;
  }

  setQuantity(quantity: number): OrderItemBuilder {
    this.item.quantity = quantity;
    this.recalculateTotal();
    return this;
  }

  setUnitPrice(price: number): OrderItemBuilder {
    this.item.unitPrice = price;
    this.recalculateTotal();
    return this;
  }

  private recalculateTotal(): void {
    const quantity = this.item.quantity || 0;
    const unitPrice = this.item.unitPrice || 0;
    this.item.totalPrice = quantity * unitPrice;
  }

  build(): OrderItem {
    if (!this.item.id || !this.item.productId) {
      throw new Error('OrderItem must have id and productId');
    }
    
    return this.item as OrderItem;
  }
}

// 订单工具类
class OrderUtils {
  // 计算订单小计
  static calculateSubtotal(items: OrderItem[]): number {
    return items.reduce((sum, item) => sum + item.totalPrice, 0);
  }

  // 计算订单总数
  static calculateTotalItems(items: OrderItem[]): number {
    return items.reduce((sum, item) => sum + item.quantity, 0);
  }

  // 检查订单是否可取消
  static isCancellable(order: Order): boolean {
    return [
      OrderStatus.PENDING,
      OrderStatus.CONFIRMED
    ].includes(order.status);
  }

  // 检查订单是否可退款
  static isRefundable(order: Order): boolean {
    return [
      OrderStatus.DELIVERED,
      OrderStatus.SHIPPED
    ].includes(order.status);
  }

  // 获取订单状态显示名称
  static getStatusDisplayName(status: OrderStatus): string {
    const names: Record<OrderStatus, string> = {
      [OrderStatus.PENDING]: 'Pending',
      [OrderStatus.CONFIRMED]: 'Confirmed',
      [OrderStatus.PROCESSING]: 'Processing',
      [OrderStatus.SHIPPED]: 'Shipped',
      [OrderStatus.DELIVERED]: 'Delivered',
      [OrderStatus.CANCELLED]: 'Cancelled',
      [OrderStatus.REFUNDED]: 'Refunded'
    };
    return names[status] || status;
  }

  // 格式化订单号
  static formatOrderNumber(id: string): string {
    return `ORD-${id.toUpperCase().slice(0, 8)}`;
  }

  // 序列化订单
  static serialize(order: Order): string {
    return JSON.stringify(order);
  }

  // 反序列化订单
  static deserialize(json: string): Order {
    return JSON.parse(json) as Order;
  }
}

export { OrderStatus, OrderBuilder, OrderItemBuilder, OrderUtils };
export type { Order, OrderItem, OrderAddress, OrderPayment };
