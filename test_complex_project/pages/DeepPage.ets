/**
 * 深层调用链页面 - 测试方法调用链的深度
 */

import { Logger } from '../utils/Logger';
import { Helper } from '../utils/Helper';

@Entry
@Component
struct DeepPage {
  @State private result: string = '';
  @State private callDepth: number = 0;

  // 第1层 - 入口
  private level1(): void {
    Logger.info('DeepPage', 'Level 1');
    this.callDepth = 1;
    this.level2();
  }

  // 第2层
  private level2(): void {
    Logger.info('DeepPage', 'Level 2');
    this.callDepth = 2;
    this.level3();
  }

  // 第3层
  private level3(): void {
    Logger.info('DeepPage', 'Level 3');
    this.callDepth = 3;
    this.level4();
  }

  // 第4层
  private level4(): void {
    Logger.info('DeepPage', 'Level 4');
    this.callDepth = 4;
    this.level5();
  }

  // 第5层
  private level5(): void {
    Logger.info('DeepPage', 'Level 5');
    this.callDepth = 5;
    this.level6();
  }

  // 第6层
  private level6(): void {
    Logger.info('DeepPage', 'Level 6');
    this.callDepth = 6;
    this.level7();
  }

  // 第7层
  private level7(): void {
    Logger.info('DeepPage', 'Level 7');
    this.callDepth = 7;
    this.level8();
  }

  // 第8层
  private level8(): void {
    Logger.info('DeepPage', 'Level 8');
    this.callDepth = 8;
    this.level9();
  }

  // 第9层
  private level9(): void {
    Logger.info('DeepPage', 'Level 9');
    this.callDepth = 9;
    this.level10();
  }

  // 第10层 - 终点
  private level10(): void {
    Logger.info('DeepPage', 'Level 10 - End');
    this.callDepth = 10;
    this.result = `Reached depth: ${this.callDepth}`;
  }

  // 分支调用链 A
  private chainA1(): void {
    this.chainA2();
  }

  private chainA2(): void {
    this.chainA3();
  }

  private chainA3(): void {
    this.chainA4();
  }

  private chainA4(): void {
    this.chainA5();
  }

  private chainA5(): void {
    Logger.info('DeepPage', 'Chain A complete');
  }

  // 分支调用链 B
  private chainB1(): void {
    this.chainB2();
  }

  private chainB2(): void {
    this.chainB3();
  }

  private chainB3(): void {
    this.chainB4();
  }

  private chainB4(): void {
    Logger.info('DeepPage', 'Chain B complete');
  }

  // 递归调用测试
  private recursiveCall(n: number): number {
    if (n <= 0) return 0;
    if (n === 1) return 1;
    return this.recursiveCall(n - 1) + this.recursiveCall(n - 2);
  }

  // 相互递归
  private isEven(n: number): boolean {
    if (n === 0) return true;
    return this.isOdd(n - 1);
  }

  private isOdd(n: number): boolean {
    if (n === 0) return false;
    return this.isEven(n - 1);
  }

  // 回调地狱模拟
  private callbackHell(): void {
    this.async1(() => {
      this.async2(() => {
        this.async3(() => {
          this.async4(() => {
            this.async5(() => {
              Logger.info('DeepPage', 'Callback hell complete');
            });
          });
        });
      });
    });
  }

  private async1(callback: Function): void {
    setTimeout(() => callback(), 10);
  }

  private async2(callback: Function): void {
    setTimeout(() => callback(), 10);
  }

  private async3(callback: Function): void {
    setTimeout(() => callback(), 10);
  }

  private async4(callback: Function): void {
    setTimeout(() => callback(), 10);
  }

  private async5(callback: Function): void {
    setTimeout(() => callback(), 10);
  }

  // Promise链
  private promiseChain(): void {
    this.promise1()
      .then(() => this.promise2())
      .then(() => this.promise3())
      .then(() => this.promise4())
      .then(() => this.promise5())
      .then(() => {
        Logger.info('DeepPage', 'Promise chain complete');
      })
      .catch(error => {
        Logger.error('DeepPage', 'Promise chain error', error);
      });
  }

  private promise1(): Promise<void> {
    return Promise.resolve();
  }

  private promise2(): Promise<void> {
    return Promise.resolve();
  }

  private promise3(): Promise<void> {
    return Promise.resolve();
  }

  private promise4(): Promise<void> {
    return Promise.resolve();
  }

  private promise5(): Promise<void> {
    return Promise.resolve();
  }

  // 复杂的条件调用链
  private conditionalChain(condition: boolean): void {
    if (condition) {
      this.branchA();
    } else {
      this.branchB();
    }
  }

  private branchA(): void {
    if (Math.random() > 0.5) {
      this.subBranchA1();
    } else {
      this.subBranchA2();
    }
  }

  private branchB(): void {
    const helper = new Helper();
    if (helper.checkCondition()) {
      this.subBranchB1();
    } else {
      this.subBranchB2();
    }
  }

  private subBranchA1(): void {
    Logger.info('DeepPage', 'Sub Branch A1');
  }

  private subBranchA2(): void {
    Logger.info('DeepPage', 'Sub Branch A2');
  }

  private subBranchB1(): void {
    Logger.info('DeepPage', 'Sub Branch B1');
  }

  private subBranchB2(): void {
    Logger.info('DeepPage', 'Sub Branch B2');
  }

  // 循环中的调用
  private loopCalls(): void {
    for (let i = 0; i < 5; i++) {
      this.loopIteration(i);
    }
  }

  private loopIteration(index: number): void {
    Logger.info('DeepPage', `Loop iteration ${index}`);
    this.nestedLoopCall(index);
  }

  private nestedLoopCall(index: number): void {
    // 嵌套循环调用
    for (let j = 0; j < 3; j++) {
      this.deepNestedCall(index, j);
    }
  }

  private deepNestedCall(i: number, j: number): void {
    Logger.info('DeepPage', `Nested call: ${i}, ${j}`);
  }

  // 事件处理器
  private onStartDeepChain(): void {
    this.level1();
  }

  private onStartChainA(): void {
    this.chainA1();
  }

  private onStartChainB(): void {
    this.chainB1();
  }

  private onRecursiveTest(): void {
    const result = this.recursiveCall(10);
    this.result = `Fibonacci(10) = ${result}`;
  }

  private onCallbackHell(): void {
    this.callbackHell();
  }

  private onPromiseChain(): void {
    this.promiseChain();
  }

  private onConditionalChain(): void {
    this.conditionalChain(Math.random() > 0.5);
  }

  private onLoopCalls(): void {
    this.loopCalls();
  }

  build() {
    Column() {
      Text('Deep Call Chain Test')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .margin(16)

      Text(`Current Depth: ${this.callDepth}`)
        .fontSize(18)
        .margin(8)

      Text(this.result)
        .fontSize(16)
        .fontColor('#666')
        .margin(8)

      // 测试按钮
      Column({ space: 8 }) {
        Button('Start Deep Chain (10 levels)')
          .onClick(() => this.onStartDeepChain())
          .width('80%')

        Button('Start Chain A')
          .onClick(() => this.onStartChainA())
          .width('80%')

        Button('Start Chain B')
          .onClick(() => this.onStartChainB())
          .width('80%')

        Button('Recursive Test')
          .onClick(() => this.onRecursiveTest())
          .width('80%')

        Button('Callback Hell')
          .onClick(() => this.onCallbackHell())
          .width('80%')

        Button('Promise Chain')
          .onClick(() => this.onPromiseChain())
          .width('80%')

        Button('Conditional Chain')
          .onClick(() => this.onConditionalChain())
          .width('80%')

        Button('Loop Calls')
          .onClick(() => this.onLoopCalls())
          .width('80%')
      }
      .margin(16)
    }
    .width('100%')
    .height('100%')
  }
}
