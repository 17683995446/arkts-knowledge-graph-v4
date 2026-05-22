/**
 * Circular_5.ets - 循环依赖组件5
 * 自引用循环依赖
 */

import { Service_005 } from '../services/Service_005';

@Component
struct Circular_5 {
  @State private selfRef: Circular_5 | null = null;
  
  private service005: Service_005 = new Service_005();
  
  // 自引用方法
  private selfReference = (): void => {
    this.selfRef = this;
    this.chain1();
  }
  
  private chain1(): void { this.chain2(); }
  private chain2(): void { this.chain3(); }
  private chain3(): void { this.chain4(); }
  private chain4(): void { this.chain5(); }
  private chain5(): void { this.chain6(); }
  private chain6(): void { this.chain7(); }
  private chain7(): void { this.chain8(); }
  private chain8(): void { this.chain9(); }
  private chain9(): void { this.chain10(); }
  
  private chain10(): void {
    if (this.selfRef) {
      this.selfRef.service005.method005();
    }
  }
  
  build() {
    Column() {
      Text('Circular_5 (Self-Referencing)')
      Button('Self Reference').onClick(this.selfReference)
    }
  }
}
