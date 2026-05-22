/**
 * Level3_D.ets - 三级组件D
 */

import { Service_017 } from '../services/Service_017';

@Component
struct Level3_D {
  @State private text: string = '';
  
  private service017: Service_017 = new Service_017();
  
  private updateText = (t: string): void => {
    this.update1(t);
  }
  
  private update1(t: string): void { this.update2(t); }
  private update2(t: string): void { this.update3(t); }
  private update3(t: string): void { this.update4(t); }
  private update4(t: string): void { this.update5(t); }
  private update5(t: string): void { this.update6(t); }
  private update6(t: string): void { this.update7(t); }
  private update7(t: string): void { this.update8(t); }
  private update8(t: string): void { this.update9(t); }
  private update9(t: string): void { this.update10(t); }
  
  private update10(t: string): void {
    this.text = t;
    this.service017.method017();
  }
  
  build() {
    TextInput({ text: this.text })
      .onChange(this.updateText)
  }
}
