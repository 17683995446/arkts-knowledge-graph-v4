/**
 * Mixin_D.ets - 混入组件D
 * 事件混入类
 */

import { Util_009 } from '../utils/Util_009';

class Mixin_D {
  private util009: Util_009 = new Util_009();
  private listeners: Array<() => void> = [];
  
  // 事件处理链
  emitEvent(): void {
    this.emit1();
  }
  
  private emit1(): void { this.emit2(); }
  private emit2(): void { this.emit3(); }
  private emit3(): void { this.emit4(); }
  private emit4(): void { this.emit5(); }
  private emit5(): void { this.emit6(); }
  private emit6(): void { this.emit7(); }
  private emit7(): void { this.emit8(); }
  private emit8(): void { this.emit9(); }
  private emit9(): void { this.emit10(); }
  
  private emit10(): void {
    this.listeners.forEach(fn => fn());
    this.util009.process009();
  }
  
  on(event: string, callback: () => void): void {
    this.listeners.push(callback);
  }
  
  off(event: string, callback: () => void): void {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }
}

export { Mixin_D };
