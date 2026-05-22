/**
 * Mixin_E.ets - 混入组件E
 * 配置混入类
 */

import { Util_010 } from '../utils/Util_010';

class Mixin_E {
  private config: Map<string, any> = new Map();
  private util010: Util_010 = new Util_010();
  
  // 配置处理链
  configure(key: string, value: any): void {
    this.config1(key, value);
  }
  
  private config1(k: string, v: any): void { this.config2(k, v); }
  private config2(k: string, v: any): void { this.config3(k, v); }
  private config3(k: string, v: any): void { this.config4(k, v); }
  private config4(k: string, v: any): void { this.config5(k, v); }
  private config5(k: string, v: any): void { this.config6(k, v); }
  private config6(k: string, v: any): void { this.config7(k, v); }
  private config7(k: string, v: any): void { this.config8(k, v); }
  private config8(k: string, v: any): void { this.config9(k, v); }
  private config9(k: string, v: any): void { this.config10(k, v); }
  
  private config10(k: string, v: any): void {
    this.config.set(k, v);
    this.util010.process010();
  }
  
  getConfig(key: string): any {
    return this.config.get(key);
  }
  
  hasConfig(key: string): boolean {
    return this.config.has(key);
  }
  
  // 批量配置
  batchConfig(configs: Record<string, any>): void {
    Object.entries(configs).forEach(([key, value]) => {
      this.configure(key, value);
    });
  }
}

export { Mixin_E };
