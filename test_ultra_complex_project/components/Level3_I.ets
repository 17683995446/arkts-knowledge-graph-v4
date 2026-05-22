/**
 * Level3_I.ets - 三级组件I
 */

import { Util_004 } from '../utils/Util_004';

@Component
struct Level3_I {
  @State private time: Date = new Date();
  
  private util004: Util_004 = new Util_004();
  
  private onTimeChange = (t: Date): void => {
    this.time1(t);
  }
  
  private time1(t: Date): void { this.time2(t); }
  private time2(t: Date): void { this.time3(t); }
  private time3(t: Date): void { this.time4(t); }
  private time4(t: Date): void { this.time5(t); }
  private time5(t: Date): void { this.time6(t); }
  private time6(t: Date): void { this.time7(t); }
  private time7(t: Date): void { this.time8(t); }
  private time8(t: Date): void { this.time9(t); }
  private time9(t: Date): void { this.time10(t); }
  
  private time10(t: Date): void {
    this.time = t;
    this.util004.process004();
  }
  
  build() {
    TimePicker({ selected: this.time })
      .onChange(this.onTimeChange)
  }
}
