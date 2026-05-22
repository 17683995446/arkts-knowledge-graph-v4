/**
 * Mixin_B.ets - 混入组件B
 * 扩展混入类
 */

import { Util_007 } from '../utils/Util_007';

class Mixin_B {
  protected util007: Util_007 = new Util_007();
  
  extendedMixin(): void {
    this.extChain1();
  }
  
  private extChain1(): void { this.extChain2(); }
  private extChain2(): void { this.extChain3(); }
  private extChain3(): void { this.extChain4(); }
  private extChain4(): void { this.extChain5(); }
  private extChain5(): void { this.extChain6(); }
  private extChain6(): void { this.extChain7(); }
  private extChain7(): void { this.extChain8(); }
  private extChain8(): void { this.extChain9(); }
  private extChain9(): void { this.extChain10(); }
  
  private extChain10(): void {
    this.util007.process007();
  }
  
  // 模板方法模式
  templateMethod(): void {
    this.step1();
    this.step2();
    this.step3();
  }
  
  protected step1(): void { console.log('step1'); }
  protected step2(): void { console.log('step2'); }
  protected step3(): void { console.log('step3'); }
}

export { Mixin_B };
