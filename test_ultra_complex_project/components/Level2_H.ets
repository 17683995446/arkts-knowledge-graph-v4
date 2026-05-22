/**
 * Level2_H.ets - 二级组件H
 */

import { Service_010 } from '../services/Service_010';
import { Level3_H } from './Level3_H';

@Component
struct Level2_H {
  @State private stepperIndex: number = 0;
  
  private service010: Service_010 = new Service_010();
  
  private nextStep = (): void => {
    this.step1();
  }
  
  private step1(): void { this.step2(); }
  private step2(): void { this.step3(); }
  private step3(): void { this.step4(); }
  private step4(): void { this.step5(); }
  private step5(): void { this.step6(); }
  private step6(): void { this.step7(); }
  private step7(): void { this.step8(); }
  private step8(): void { this.step9(); }
  private step9(): void { this.step10(); }
  
  private step10(): void {
    this.stepperIndex++;
    this.service010.method010();
  }
  
  build() {
    Column() {
      Level3_H()
      Stepper() {
        StepperItem() { Text('Step 1') }
        StepperItem() { Text('Step 2') }
      }
      .onFinish(this.nextStep)
    }
  }
}
