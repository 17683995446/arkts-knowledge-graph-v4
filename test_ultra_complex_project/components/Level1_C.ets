/**
 * Level1_C.ets - 一级组件C
 * 复杂状态管理、多服务协调
 */

import { Service_004 } from '../services/Service_004';
import { Service_005 } from '../services/Service_005';
import { Model_002 } from '../models/Model_002';
import { Level2_C } from './Level2_C';

@Component
@Reusable
struct Level1_C {
  @State @Watch('onDataChange') data: Model_002 = new Model_002();
  @Provide theme: string = 'light';
  @Consume activeTab: number;
  
  private service004: Service_004 = new Service_004();
  private service005: Service_005 = new Service_005();
  
  // 复杂箭头函数
  private complexHandler = (a: number, b: string, c: boolean): string => {
    return this.processComplexInput(a, b, c);
  }
  
  private processComplexInput(a: number, b: string, c: boolean): string {
    return this.step1Complex(a, b, c);
  }
  
  // 10层嵌套
  private step1Complex(a: number, b: string, c: boolean): string {
    return this.step2Complex(a, b, c);
  }
  
  private step2Complex(a: number, b: string, c: boolean): string {
    return this.step3Complex(a, b, c);
  }
  
  private step3Complex(a: number, b: string, c: boolean): string {
    return this.step4Complex(a, b, c);
  }
  
  private step4Complex(a: number, b: string, c: boolean): string {
    return this.step5Complex(a, b, c);
  }
  
  private step5Complex(a: number, b: string, c: boolean): string {
    return this.step6Complex(a, b, c);
  }
  
  private step6Complex(a: number, b: string, c: boolean): string {
    return this.step7Complex(a, b, c);
  }
  
  private step7Complex(a: number, b: string, c: boolean): string {
    return this.step8Complex(a, b, c);
  }
  
  private step8Complex(a: number, b: string, c: boolean): string {
    return this.step9Complex(a, b, c);
  }
  
  private step9Complex(a: number, b: string, c: boolean): string {
    return this.step10Complex(a, b, c);
  }
  
  private step10Complex(a: number, b: string, c: boolean): string {
    return `${a}-${b}-${c}`;
  }
  
  // 多异步协调
  private async coordinateServices(): Promise<void> {
    const [result4, result5] = await Promise.all([
      this.service004.method004(),
      this.service005.method005()
    ]);
    this.processCoordinatedResults(result4, result5);
  }
  
  private processCoordinatedResults(r4: any, r5: any): void {
    console.log(r4, r5);
  }
  
  private onDataChange(): void {
    this.coordinateServices();
  }
  
  // 特殊字符方法名
  private $special$method$(): void {
    console.log('special chars');
  }
  
  aboutToAppear(): void {
    this.coordinateServices();
  }
  
  aboutToRecycle(): void {
    console.log('recycling');
  }
  
  build() {
    Stack() {
      Column() {
        Level2_C()
      }
    }
  }
}
