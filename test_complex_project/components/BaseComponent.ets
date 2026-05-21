/**
 * 基类组件 - 用于测试继承和抽象方法
 * 包含抽象方法、静态方法、泛型方法等复杂结构
 */

// 基础接口定义
interface IBaseComponent {
  id: string;
  render(): void;
}

// 抽象基类组件
@Component
abstract struct BaseComponent<T extends IBaseComponent> {
  // 装饰器组合测试 - 多种装饰器叠加
  @State protected data: T | null = null;
  @Prop @Watch('onDataChange') config: Record<string, any> = {};
  @StorageLink('globalTheme') theme: string = 'light';
  @Provide @Consume context: Record<string, any>;

  // 静态成员
  private static instanceCount: number = 0;
  private static readonly MAX_INSTANCES: number = 100;

  // 抽象方法声明
  abstract buildContent(): void;
  abstract onDataChange(propName: string): void;

  // 构造函数
  aboutToAppear(): void {
    BaseComponent.instanceCount++;
    this.initialize();
  }

  aboutToDisappear(): void {
    BaseComponent.instanceCount--;
    this.cleanup();
  }

  // 初始化方法
  private initialize(): void {
    if (this.data) {
      this.processData(this.data);
    }
  }

  // 清理方法
  private cleanup(): void {
    this.data = null;
  }

  // 泛型方法
  protected processData<U extends T>(input: U): U {
    // 深拷贝逻辑
    const cloned = JSON.parse(JSON.stringify(input));
    return cloned as U;
  }

  // 静态方法
  static getInstanceCount(): number {
    return BaseComponent.instanceCount;
  }

  // 箭头函数属性
  handleEvent = (event: Event): void => {
    console.log('Event handled:', event.type);
    this.onEvent(event);
  };

  // 异步方法
  async fetchData(): Promise<T | null> {
    try {
      const response = await this.performRequest();
      return this.processData(response);
    } catch (error) {
      this.handleError(error);
      return null;
    }
  }

  // 受保护的方法
  protected onEvent(event: Event): void {
    // 默认实现
  }

  // 私有方法
  private performRequest(): Promise<any> {
    return new Promise((resolve) => {
      setTimeout(() => resolve({ id: 'test' }), 100);
    });
  }

  private handleError(error: Error): void {
    console.error('Error:', error.message);
  }

  // 计算属性
  get isValid(): boolean {
    return this.data !== null && BaseComponent.instanceCount < BaseComponent.MAX_INSTANCES;
  }

  // 嵌套函数调用测试
  complexOperation(): void {
    const step1 = () => this.validate();
    const step2 = () => this.transform();
    const step3 = () => this.save();

    if (step1()) {
      const result = step2();
      if (result) {
        step3();
      }
    }
  }

  private validate(): boolean {
    return this.isValid;
  }

  private transform(): boolean {
    return true;
  }

  private save(): void {
    // 保存逻辑
  }

  build() {
    Column() {
      // 调用抽象方法
      this.buildContent();
    }
  }
}

// 辅助接口
interface Event {
  type: string;
  target: any;
}
