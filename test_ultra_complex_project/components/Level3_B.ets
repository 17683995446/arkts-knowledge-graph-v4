/**
 * Level3_B.ets - 三级组件B
 */

import { Service_015 } from '../services/Service_015';

@Component
struct Level3_B {
  @State private value: number = 0;
  
  private service015: Service_015 = new Service_015();
  
  private processValue = (v: number): void => {
    this.proc1(v);
  }
  
  private proc1(v: number): void { this.proc2(v); }
  private proc2(v: number): void { this.proc3(v); }
  private proc3(v: number): void { this.proc4(v); }
  private proc4(v: number): void { this.proc5(v); }
  private proc5(v: number): void { this.proc6(v); }
  private proc6(v: number): void { this.proc7(v); }
  private proc7(v: number): void { this.proc8(v); }
  private proc8(v: number): void { this.proc9(v); }
  private proc9(v: number): void { this.proc10(v); }
  
  private proc10(v: number): void {
    this.value = v;
    this.service015.method015();
  }
  
  build() {
    Text(`Level3_B: ${this.value}`)
  }
}
