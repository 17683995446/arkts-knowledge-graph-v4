/**
 * Level3_E.ets - 三级组件E
 */

import { Service_018 } from '../services/Service_018';

@Component
struct Level3_E {
  @State private count: number = 0;
  
  private service018: Service_018 = new Service_018();
  
  private increment = (): void => {
    this.inc1();
  }
  
  private inc1(): void { this.inc2(); }
  private inc2(): void { this.inc3(); }
  private inc3(): void { this.inc4(); }
  private inc4(): void { this.inc5(); }
  private inc5(): void { this.inc6(); }
  private inc6(): void { this.inc7(); }
  private inc7(): void { this.inc8(); }
  private inc8(): void { this.inc9(); }
  private inc9(): void { this.inc10(); }
  
  private inc10(): void {
    this.count++;
    this.service018.method018();
  }
  
  build() {
    Button(`Count: ${this.count}`)
      .onClick(this.increment)
  }
}
