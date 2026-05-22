/**
 * Level1_F.ets - 一级组件F
 * 复杂表单处理、验证链
 */

import { Service_008 } from '../services/Service_008';
import { Service_009 } from '../services/Service_009';
import { Level2_G } from './Level2_G';

@Component
struct Level1_F {
  @State private formData: Map<string, string> = new Map();
  @State private errors: string[] = [];
  
  private service008: Service_008 = new Service_008();
  private service009: Service_009 = new Service_009();
  
  // 表单验证链
  private validateForm = (): boolean => {
    return this.validation1();
  }
  
  private validation1(): boolean {
    return this.validation2();
  }
  
  private validation2(): boolean {
    return this.validation3();
  }
  
  private validation3(): boolean {
    return this.validation4();
  }
  
  private validation4(): boolean {
    return this.validation5();
  }
  
  private validation5(): boolean {
    return this.validation6();
  }
  
  private validation6(): boolean {
    return this.validation7();
  }
  
  private validation7(): boolean {
    return this.validation8();
  }
  
  private validation8(): boolean {
    return this.validation9();
  }
  
  private validation9(): boolean {
    return this.validation10();
  }
  
  private validation10(): boolean {
    return this.errors.length === 0;
  }
  
  // 提交处理链
  private async submitForm(): Promise<void> {
    if (!this.validateForm()) return;
    await this.submitStep1();
  }
  
  private async submitStep1(): Promise<void> {
    await this.submitStep2();
  }
  
  private async submitStep2(): Promise<void> {
    await this.submitStep3();
  }
  
  private async submitStep3(): Promise<void> {
    await this.service008.submitData(this.formData);
  }
  
  // 字段验证
  private validateField(field: string, value: string): void {
    const validators = [
      (v: string) => v.length > 0,
      (v: string) => v.length < 100,
      (v: string) => !v.includes('<script>')
    ];
    
    const isValid = validators.every(fn => fn(value));
    if (!isValid) {
      this.errors.push(`${field} is invalid`);
    }
  }
  
  build() {
    Column() {
      Level2_G()
      Button('Submit')
        .onClick(() => this.submitForm())
    }
  }
}
