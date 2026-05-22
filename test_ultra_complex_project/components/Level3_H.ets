/**
 * Level3_H.ets - 三级组件H
 */

import { Util_003 } from '../utils/Util_003';

@Component
struct Level3_H {
  @State private date: Date = new Date();
  
  private util003: Util_003 = new Util_003();
  
  private onDateChange = (d: Date): void => {
    this.date1(d);
  }
  
  private date1(d: Date): void { this.date2(d); }
  private date2(d: Date): void { this.date3(d); }
  private date3(d: Date): void { this.date4(d); }
  private date4(d: Date): void { this.date5(d); }
  private date5(d: Date): void { this.date6(d); }
  private date6(d: Date): void { this.date7(d); }
  private date7(d: Date): void { this.date8(d); }
  private date8(d: Date): void { this.date9(d); }
  private date9(d: Date): void { this.date10(d); }
  
  private date10(d: Date): void {
    this.date = d;
    this.util003.process003();
  }
  
  build() {
    DatePicker({ selected: this.date })
      .onChange(this.onDateChange)
  }
}
