/**
 * Level1_E.ets - 一级组件E
 * 复杂动画、生命周期管理
 */

import { Service_007 } from '../services/Service_007';
import { Util_001 } from '../utils/Util_001';
import { Level2_F } from './Level2_F';

@Component
struct Level1_E {
  @State private animationState: number = 0;
  @State private opacity: number = 1.0;
  
  private service007: Service_007 = new Service_007();
  private util001: Util_001 = new Util_001();
  
  // 动画控制链
  private startAnimation = (): void => {
    this.animate1();
  }
  
  private animate1(): void {
    this.animate2();
  }
  
  private animate2(): void {
    this.animate3();
  }
  
  private animate3(): void {
    this.animate4();
  }
  
  private animate4(): void {
    this.animate5();
  }
  
  private animate5(): void {
    this.animate6();
  }
  
  private animate6(): void {
    this.animate7();
  }
  
  private animate7(): void {
    this.animate8();
  }
  
  private animate8(): void {
    this.animate9();
  }
  
  private animate9(): void {
    this.animate10();
  }
  
  private animate10(): void {
    this.animationState = 1;
    this.service007.method007();
  }
  
  // 异步动画序列
  private async runAnimationSequence(): Promise<void> {
    await this.delay(100);
    this.startAnimation();
    await this.delay(200);
    this.opacity = 0.5;
  }
  
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // 工具方法链
  private processWithUtils(): void {
    const result = this.util001.process001();
    this.util002Process(result);
  }
  
  private util002Process(data: string): void {
    console.log(data);
  }
  
  aboutToAppear(): void {
    this.runAnimationSequence();
  }
  
  onPageShow(): void {
    console.log('page shown');
  }
  
  build() {
    Column() {
      Level2_F()
        .opacity(this.opacity)
        .animation({ duration: 300 })
    }
  }
}
