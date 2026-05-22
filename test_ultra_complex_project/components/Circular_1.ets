/**
 * Circular_1.ets - 循环依赖组件1
 * 与Circular_2形成循环依赖
 */

import { Circular_2 } from './Circular_2';
import { Service_001 } from '../services/Service_001';

@Component
struct Circular_1 {
  @State private data: string = '';
  
  private service001: Service_001 = new Service_001();
  
  // 调用Circular_2的方法
  private callCircular2 = (): void => {
    const c2 = new Circular_2();
    c2.methodFromC1();
  }
  
  // 被Circular_2调用的方法
  methodFromC2(): void {
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
    this.service001.method001();
  }
  
  build() {
    Column() {
      Text('Circular_1')
      Button('Call C2').onClick(this.callCircular2)
    }
  }
}
