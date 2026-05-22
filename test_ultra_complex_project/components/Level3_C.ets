/**
 * Level3_C.ets - 三级组件C
 */

import { Service_016 } from '../services/Service_016';

@Component
struct Level3_C {
  @State private flag: boolean = false;
  
  private service016: Service_016 = new Service_016();
  
  private toggleFlag = (): void => {
    this.toggle1();
  }
  
  private toggle1(): void { this.toggle2(); }
  private toggle2(): void { this.toggle3(); }
  private toggle3(): void { this.toggle4(); }
  private toggle4(): void { this.toggle5(); }
  private toggle5(): void { this.toggle6(); }
  private toggle6(): void { this.toggle7(); }
  private toggle7(): void { this.toggle8(); }
  private toggle8(): void { this.toggle9(); }
  private toggle9(): void { this.toggle10(); }
  
  private toggle10(): void {
    this.flag = !this.flag;
    this.service016.method016();
  }
  
  build() {
    Text(`Level3_C: ${this.flag}`)
      .onClick(this.toggleFlag)
  }
}
