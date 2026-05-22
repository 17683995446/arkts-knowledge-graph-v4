/**
 * Level1_D.ets - 一级组件D
 * 深度嵌套UI、复杂事件处理
 */

import { Service_006 } from '../services/Service_006';
import { Level2_D } from './Level2_D';
import { Level2_E } from './Level2_E';

@Component
struct Level1_D {
  @State private nestedLevel: number = 0;
  @State private isExpanded: boolean = false;
  
  private service006: Service_006 = new Service_006();
  
  // 事件处理器链
  private handleExpand = (): void => {
    this.toggleExpand1();
  }
  
  private toggleExpand1(): void {
    this.toggleExpand2();
  }
  
  private toggleExpand2(): void {
    this.toggleExpand3();
  }
  
  private toggleExpand3(): void {
    this.toggleExpand4();
  }
  
  private toggleExpand4(): void {
    this.toggleExpand5();
  }
  
  private toggleExpand5(): void {
    this.toggleExpand6();
  }
  
  private toggleExpand6(): void {
    this.toggleExpand7();
  }
  
  private toggleExpand7(): void {
    this.toggleExpand8();
  }
  
  private toggleExpand8(): void {
    this.toggleExpand9();
  }
  
  private toggleExpand9(): void {
    this.toggleExpand10();
  }
  
  private toggleExpand10(): void {
    this.isExpanded = !this.isExpanded;
    this.service006.method006();
  }
  
  // 递归式调用模式
  private processNestedData(data: any, depth: number): any {
    if (depth <= 0) {
      return data;
    }
    return this.processNestedData(this.transformData(data), depth - 1);
  }
  
  private transformData(data: any): any {
    return { ...data, transformed: true };
  }
  
  // 高阶函数
  private createHandler(prefix: string): (msg: string) => void {
    return (msg: string): void => {
      console.log(`${prefix}: ${msg}`);
    };
  }
  
  // 立即执行函数风格
  private initWithIIFE(): void {
    const config = ((): { value: number } => {
      return { value: 42 };
    })();
    console.log(config.value);
  }
  
  build() {
    Column() {
      if (this.isExpanded) {
        Level2_D()
        Level2_E()
      }
      Button(this.isExpanded ? 'Collapse' : 'Expand')
        .onClick(this.handleExpand)
    }
  }
}
