/**
 * Circular_2.ets - 循环依赖组件2
 * 与Circular_1形成循环依赖
 */

import { Circular_1 } from './Circular_1';
import { Service_002 } from '../services/Service_002';

@Component
struct Circular_2 {
  @State private value: number = 0;
  
  private service002: Service_002 = new Service_002();
  
  // 调用Circular_1的方法
  private callCircular1 = (): void => {
    const c1 = new Circular_1();
    c1.methodFromC2();
  }
  
  // 被Circular_1调用的方法
  methodFromC1(): void {
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
    this.service002.method002();
  }
  
  build() {
    Column() {
      Text('Circular_2')
      Button('Call C1').onClick(this.callCircular1)
    }
  }
}
