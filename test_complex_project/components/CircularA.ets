/**
 * 循环依赖测试 - 组件A
 * 测试系统对循环引用的检测和处理能力
 */

// 导入B（形成循环依赖）
import { CircularB } from './CircularB';
import { CircularC } from './CircularC';

// 组件A
@Component
struct CircularA {
  @State dataA: string = 'A';
  @State refB: CircularB | null = null;

  aboutToAppear(): void {
    // 间接引用B
    this.initializeWithB();
  }

  private initializeWithB(): void {
    // 这里会触发对B的引用
    console.log('Initializing A with reference to B');
  }

  // 方法中调用B的方法
  public callBMethod(): void {
    if (this.refB) {
      this.refB.methodFromA();
    }
  }

  // 接受B作为参数
  public setReference(b: CircularB): void {
    this.refB = b;
  }

  // 复杂类型引用
  public processBData(data: BDataType): ProcessedData {
    return {
      source: 'A',
      original: data,
      processed: true
    };
  }

  build() {
    Column() {
      Text(`Component ${this.dataA}`)
        .fontSize(20)
      // 嵌套使用B
      CircularB()
      // 使用C（C又引用A）
      CircularC()
    }
  }
}

// A特有的数据类型
interface BDataType {
  id: string;
  value: number;
  metadata: Record<string, any>;
}

interface ProcessedData {
  source: string;
  original: BDataType;
  processed: boolean;
}

// 导出供B使用
export { CircularA };
export type { BDataType, ProcessedData };
