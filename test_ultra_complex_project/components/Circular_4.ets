/**
 * Circular_4.ets - 循环依赖组件4
 * 与Circular_3形成循环依赖
 */

import { Circular_3 } from './Circular_3';
import { Service_004 } from '../services/Service_004';

@Component
struct Circular_4 {
  @State private count: number = 0;
  
  private service004: Service_004 = new Service_004();
  
  private triggerC3 = (): void => {
    const c3 = new Circular_3();
    c3.triggerC4();
  }
  
  triggerC3(): void {
    this.handle1();
  }
  
  private handle1(): void { this.handle2(); }
  private handle2(): void { this.handle3(); }
  private handle3(): void { this.handle4(); }
  private handle4(): void { this.handle5(); }
  private handle5(): void { this.handle6(); }
  private handle6(): void { this.handle7(); }
  private handle7(): void { this.handle8(); }
  private handle8(): void { this.handle9(); }
  private handle9(): void { this.handle10(); }
  
  private handle10(): void {
    this.service004.method004();
  }
  
  build() {
    Column() {
      Text('Circular_4')
      Button('Trigger C3').onClick(this.triggerC3)
    }
  }
}
