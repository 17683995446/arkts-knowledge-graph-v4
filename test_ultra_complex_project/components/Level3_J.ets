/**
 * Level3_J.ets - 三级组件J
 */

import { Util_005 } from '../utils/Util_005';

@Component
struct Level3_J {
  @State private index: number = 0;
  
  private util005: Util_005 = new Util_005();
  
  private onIndexChange = (i: number): void => {
    this.index1(i);
  }
  
  private index1(i: number): void { this.index2(i); }
  private index2(i: number): void { this.index3(i); }
  private index3(i: number): void { this.index4(i); }
  private index4(i: number): void { this.index5(i); }
  private index5(i: number): void { this.index6(i); }
  private index6(i: number): void { this.index7(i); }
  private index7(i: number): void { this.index8(i); }
  private index8(i: number): void { this.index9(i); }
  private index9(i: number): void { this.index10(i); }
  
  private index10(i: number): void {
    this.index = i;
    this.util005.process005();
  }
  
  build() {
    TextPicker({ range: ['A', 'B', 'C'] })
      .onChange(this.onIndexChange)
  }
}
