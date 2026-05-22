/**
 * Level1_A.ets - 一级组件A
 * 包含多层嵌套方法调用、复杂装饰器组合
 */

import { Service_001 } from '../services/Service_001';
import { Service_002 } from '../services/Service_002';
import { Model_001 } from '../models/Model_001';

@Component
@Entry
struct Level1_A {
  @State private data: string = '';
  @Prop propValue: number = 0;
  @StorageLink('theme') theme: string = 'light';
  
  private service001: Service_001 = new Service_001();
  private service002: Service_002 = new Service_002();
  
  // 箭头函数属性
  private handleClick = (event: ClickEvent): void => {
    this.processClickEvent(event);
  }
  
  // 异步箭头函数
  private asyncHandle = async (data: string): Promise<string> => {
    return await this.processAsyncData(data);
  }
  
  // 静态方法
  static getComponentName(): string {
    return 'Level1_A';
  }
  
  // 私有方法
  private processClickEvent(event: ClickEvent): void {
    this.step1(event);
  }
  
  // 10层嵌套调用
  private step1(event: ClickEvent): void {
    this.step2(event);
  }
  
  private step2(event: ClickEvent): void {
    this.step3(event);
  }
  
  private step3(event: ClickEvent): void {
    this.step4(event);
  }
  
  private step4(event: ClickEvent): void {
    this.step5(event);
  }
  
  private step5(event: ClickEvent): void {
    this.step6(event);
  }
  
  private step6(event: ClickEvent): void {
    this.step7(event);
  }
  
  private step7(event: ClickEvent): void {
    this.step8(event);
  }
  
  private step8(event: ClickEvent): void {
    this.step9(event);
  }
  
  private step9(event: ClickEvent): void {
    this.step10(event);
  }
  
  private step10(event: ClickEvent): void {
    console.log('Level1_A: step10 reached');
    this.service001.method001();
  }
  
  // 异步方法
  private async processAsyncData(data: string): Promise<string> {
    const result = await this.service002.method002();
    return result + data;
  }
  
  // 匿名函数
  private executeCallback(): void {
    const callback = function(): void {
      console.log('anonymous callback');
    };
    callback();
  }
  
  // 空方法 - 边界情况
  private emptyMethod(): void {}
  
  // 超长方法名 - 边界情况
  private thisIsAVeryLongMethodNameThatTestsTheSystemsAbilityToHandleExtremelyLongIdentifiersWithoutBreakingOrCausingPerformanceIssues(): void {
    console.log('long method name');
  }
  
  aboutToAppear(): void {
    this.service001.init();
  }
  
  build() {
    Column() {
      Text('Level1_A Component')
        .fontSize(20)
        .onClick(this.handleClick)
      
      Button('Click Me')
        .onClick((event: ClickEvent) => {
          this.step1(event);
        })
    }
  }
}
