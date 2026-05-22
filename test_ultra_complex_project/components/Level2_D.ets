/**
 * Level2_D.ets - 二级组件D
 */

import { Service_006 } from '../services/Service_006';
import { Level3_D } from './Level3_D';

@Component
struct Level2_D {
  @State private isVisible: boolean = true;
  
  private service006: Service_006 = new Service_006();
  
  private toggleVisibility = (): void => {
    this.toggle1();
  }
  
  private toggle1(): void { this.toggle2(); }
  private toggle2(): void { this.toggle3(); }
  private toggle3(): void { this.toggle4(); }
  private toggle4(): void { this.toggle5(); }
  private toggle5(): void { this.toggle6(); }
  private toggle6(): void { this.toggle7(); }
  private toggle7(): void { this.toggle8(); }
  private toggle8(): void { this.toggle9(); }
  private toggle9(): void { this.toggle10(); }
  
  private toggle10(): void {
    this.isVisible = !this.isVisible;
    this.service006.method006();
  }
  
  build() {
    Stack() {
      if (this.isVisible) {
        Level3_D()
      }
    }
  }
}
