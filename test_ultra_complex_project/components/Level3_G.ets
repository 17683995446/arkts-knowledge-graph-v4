/**
 * Level3_G.ets - 三级组件G
 */

import { Service_020 } from '../services/Service_020';

@Component
struct Level3_G {
  @State private checked: boolean = false;
  
  private service020: Service_020 = new Service_020();
  
  private onCheck = (v: boolean): void => {
    this.check1(v);
  }
  
  private check1(v: boolean): void { this.check2(v); }
  private check2(v: boolean): void { this.check3(v); }
  private check3(v: boolean): void { this.check4(v); }
  private check4(v: boolean): void { this.check5(v); }
  private check5(v: boolean): void { this.check6(v); }
  private check6(v: boolean): void { this.check7(v); }
  private check7(v: boolean): void { this.check8(v); }
  private check8(v: boolean): void { this.check9(v); }
  private check9(v: boolean): void { this.check10(v); }
  
  private check10(v: boolean): void {
    this.checked = v;
    this.service020.method020();
  }
  
  build() {
    Checkbox()
      .select(this.checked)
      .onChange(this.onCheck)
  }
}
