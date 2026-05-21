/**
 * 循环依赖测试 - 组件B
 * 与CircularA形成循环依赖
 */

// 导入A（形成循环依赖）
import { CircularA, BDataType } from './CircularA';

// 组件B
@Component
struct CircularB {
  @State dataB: string = 'B';
  @State refA: CircularA | null = null;

  aboutToAppear(): void {
    this.initializeWithA();
  }

  private initializeWithA(): void {
    console.log('Initializing B with reference to A');
  }

  // 被A调用的方法
  public methodFromA(): void {
    console.log('Method called from A');
    this.internalProcess();
  }

  // 调用A的方法
  public callAMethod(): void {
    if (this.refA) {
      this.refA.callBMethod();
    }
  }

  private internalProcess(): void {
    // 内部处理逻辑
    const data: BDataType = {
      id: 'test',
      value: 100,
      metadata: {}
    };
    if (this.refA) {
      this.refA.processBData(data);
    }
  }

  // 接受A作为参数
  public setReference(a: CircularA): void {
    this.refA = a;
  }

  build() {
    Column() {
      Text(`Component ${this.dataB}`)
        .fontSize(18)
      // 嵌套使用A
      CircularA()
    }
    .padding(10)
  }
}

// B特有的类型和接口
interface ADataType {
  name: string;
  items: string[];
}

class BHelper {
  static processAData(data: ADataType): string {
    return data.items.join(',');
  }
}

export { CircularB, BHelper };
export type { ADataType };
