/**
 * Level2_A.ets - 二级组件A
 * 嵌套在Level1_B中
 */

import { Service_003 } from '../services/Service_003';
import { Level3_A } from './Level3_A';

@Component
struct Level2_A {
  @State private localState: string = '';
  @Prop parentData: string;
  
  private service003: Service_003 = new Service_003();
  
  // 嵌套处理链
  private handleAction = (): void => {
    this.action1();
  }
  
  private action1(): void { this.action2(); }
  private action2(): void { this.action3(); }
  private action3(): void { this.action4(); }
  private action4(): void { this.action5(); }
  private action5(): void { this.action6(); }
  private action6(): void { this.action7(); }
  private action7(): void { this.action8(); }
  private action8(): void { this.action9(); }
  private action9(): void { this.action10(); }
  
  private action10(): void {
    this.localState = 'completed';
    this.service003.method003();
  }
  
  build() {
    Row() {
      Level3_A()
      Text('Level2_A')
    }
  }
}
