/**
 * Level2_B.ets - 二级组件B
 */

import { Service_004 } from '../services/Service_004';
import { Level3_B } from './Level3_B';

@Component
struct Level2_B {
  @State private count: number = 0;
  
  private service004: Service_004 = new Service_004();
  
  private increment = (): void => {
    this.increment1();
  }
  
  private increment1(): void { this.increment2(); }
  private increment2(): void { this.increment3(); }
  private increment3(): void { this.increment4(); }
  private increment4(): void { this.increment5(); }
  private increment5(): void { this.increment6(); }
  private increment6(): void { this.increment7(); }
  private increment7(): void { this.increment8(); }
  private increment8(): void { this.increment9(); }
  private increment9(): void { this.increment10(); }
  
  private increment10(): void {
    this.count++;
    this.service004.method004();
  }
  
  build() {
    Column() {
      Level3_B()
      Button(`Count: ${this.count}`)
        .onClick(this.increment)
    }
  }
}
