/**
 * Level2_J.ets - 二级组件J
 */

import { Service_012 } from '../services/Service_012';
import { Level3_J } from './Level3_J';

@Component
struct Level2_J {
  @State private toggleState: boolean = false;
  
  private service012: Service_012 = new Service_012();
  
  private onToggle = (isOn: boolean): void => {
    this.toggle1(isOn);
  }
  
  private toggle1(v: boolean): void { this.toggle2(v); }
  private toggle2(v: boolean): void { this.toggle3(v); }
  private toggle3(v: boolean): void { this.toggle4(v); }
  private toggle4(v: boolean): void { this.toggle5(v); }
  private toggle5(v: boolean): void { this.toggle6(v); }
  private toggle6(v: boolean): void { this.toggle7(v); }
  private toggle7(v: boolean): void { this.toggle8(v); }
  private toggle8(v: boolean): void { this.toggle9(v); }
  private toggle9(v: boolean): void { this.toggle10(v); }
  
  private toggle10(v: boolean): void {
    this.toggleState = v;
    this.service012.method012();
  }
  
  build() {
    Column() {
      Level3_J()
      Toggle({ type: ToggleType.Switch, isOn: this.toggleState })
        .onChange(this.onToggle)
    }
  }
}
