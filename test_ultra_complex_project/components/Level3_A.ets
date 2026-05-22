/**
 * Level3_A.ets - 三级组件A
 * 最深层次嵌套组件
 */

import { Service_013 } from '../services/Service_013';
import { Service_014 } from '../services/Service_014';

@Component
struct Level3_A {
  @State private deepState: string = 'deep';
  
  private service013: Service_013 = new Service_013();
  private service014: Service_014 = new Service_014();
  
  // 深层处理链
  private deepAction = (): void => {
    this.deep1();
  }
  
  private deep1(): void { this.deep2(); }
  private deep2(): void { this.deep3(); }
  private deep3(): void { this.deep4(); }
  private deep4(): void { this.deep5(); }
  private deep5(): void { this.deep6(); }
  private deep6(): void { this.deep7(); }
  private deep7(): void { this.deep8(); }
  private deep8(): void { this.deep9(); }
  private deep9(): void { this.deep10(); }
  
  private deep10(): void {
    this.deepState = 'processed';
    this.service013.method013();
    this.service014.method014();
  }
  
  build() {
    Text(`Level3_A: ${this.deepState}`)
      .onClick(this.deepAction)
  }
}
