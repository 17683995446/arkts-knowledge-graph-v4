/**
 * Level2_E.ets - 二级组件E
 */

import { Service_007 } from '../services/Service_007';
import { Level3_E } from './Level3_E';

@Component
struct Level2_E {
  @State private progress: number = 0;
  
  private service007: Service_007 = new Service_007();
  
  private updateProgress = (value: number): void => {
    this.progress1(value);
  }
  
  private progress1(v: number): void { this.progress2(v); }
  private progress2(v: number): void { this.progress3(v); }
  private progress3(v: number): void { this.progress4(v); }
  private progress4(v: number): void { this.progress5(v); }
  private progress5(v: number): void { this.progress6(v); }
  private progress6(v: number): void { this.progress7(v); }
  private progress7(v: number): void { this.progress8(v); }
  private progress8(v: number): void { this.progress9(v); }
  private progress9(v: number): void { this.progress10(v); }
  
  private progress10(v: number): void {
    this.progress = v;
    this.service007.method007();
  }
  
  build() {
    Column() {
      Level3_E()
      Progress({ value: this.progress, total: 100 })
    }
  }
}
