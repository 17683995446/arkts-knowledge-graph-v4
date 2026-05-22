/**
 * Mixin_A.ets - 混入组件A
 * 基础混入类
 */

import { Util_006 } from '../utils/Util_006';

class Mixin_A {
  protected util006: Util_006 = new Util_006();
  
  // 混入方法
  mixinMethod(): void {
    this.mixinChain1();
  }
  
  private mixinChain1(): void { this.mixinChain2(); }
  private mixinChain2(): void { this.mixinChain3(); }
  private mixinChain3(): void { this.mixinChain4(); }
  private mixinChain4(): void { this.mixinChain5(); }
  private mixinChain5(): void { this.mixinChain6(); }
  private mixinChain6(): void { this.mixinChain7(); }
  private mixinChain7(): void { this.mixinChain8(); }
  private mixinChain8(): void { this.mixinChain9(); }
  private mixinChain9(): void { this.mixinChain10(); }
  
  private mixinChain10(): void {
    this.util006.process006();
  }
  
  // 可被子类覆盖的方法
  overridableMethod(): string {
    return 'Mixin_A';
  }
  
  // 静态混入方法
  static staticMixinMethod(): void {
    console.log('static mixin');
  }
}

export { Mixin_A };
