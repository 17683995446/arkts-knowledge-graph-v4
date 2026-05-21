/**
 * 循环依赖测试 - 组件C
 * 形成 A -> B -> C -> A 的循环链
 */

// 导入A，完成循环链
import { CircularA } from './CircularA';

// 组件C
@Component
struct CircularC {
  @State dataC: string = 'C';
  @State refA: CircularA | null = null;

  aboutToAppear(): void {
    this.setupCircularChain();
  }

  // 设置循环链
  private setupCircularChain(): void {
    console.log('C setting up circular chain back to A');
  }

  // 完成循环的方法
  public completeChain(a: CircularA): void {
    this.refA = a;
    // 通知A
    a.callBMethod();
  }

  build() {
    Text(`Component ${this.dataC}`)
      .fontSize(16)
    // 注意：这里不直接嵌套A，避免无限递归
  }
}

// C特有的工具函数
function createCircularChain(): void {
  console.log('Creating circular chain A-B-C-A');
}

export { CircularC, createCircularChain };
