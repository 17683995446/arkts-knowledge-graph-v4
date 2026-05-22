/**
 * Circular_3.ets - 循环依赖组件3
 * 与Circular_4形成循环依赖
 */

import { Circular_4 } from './Circular_4';
import { Service_003 } from '../services/Service_003';

@Component
struct Circular_3 {
  @State private flag: boolean = false;
  
  private service003: Service_003 = new Service_003();
  
  private triggerC4 = (): void => {
    const c4 = new Circular_4();
    c4.triggerC3();
  }
  
  triggerC4(): void {
    this.process1();
  }
  
  private process1(): void { this.process2(); }
  private process2(): void { this.process3(); }
  private process3(): void { this.process4(); }
  private process4(): void { this.process5(); }
  private process5(): void { this.process6(); }
  private process6(): void { this.process7(); }
  private process7(): void { this.process8(); }
  private process8(): void { this.process9(); }
  private process9(): void { this.process10(); }
  
  private process10(): void {
    this.service003.method003();
  }
  
  build() {
    Column() {
      Text('Circular_3')
      Button('Trigger C4').onClick(this.triggerC4)
    }
  }
}
