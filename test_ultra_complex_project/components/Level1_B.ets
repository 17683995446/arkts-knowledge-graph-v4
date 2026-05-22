/**
 * Level1_B.ets - 一级组件B
 * 继承模式、混入模式
 */

import { Level2_A } from './Level2_A';
import { Level2_B } from './Level2_B';
import { Mixin_A } from './Mixin_A';
import { Service_003 } from '../services/Service_003';

@Component
@CustomDialog
struct Level1_B extends Mixin_A {
  @State private items: string[] = [];
  @Link selectedItem: string;
  
  private service003: Service_003 = new Service_003();
  
  // 回调函数
  private onItemSelected = (item: string, index: number): void => {
    this.handleItemSelection(item, index);
  }
  
  private handleItemSelection(item: string, index: number): void {
    this.processItem1(item, index);
  }
  
  // 10层嵌套
  private processItem1(item: string, index: number): void {
    this.processItem2(item, index);
  }
  
  private processItem2(item: string, index: number): void {
    this.processItem3(item, index);
  }
  
  private processItem3(item: string, index: number): void {
    this.processItem4(item, index);
  }
  
  private processItem4(item: string, index: number): void {
    this.processItem5(item, index);
  }
  
  private processItem5(item: string, index: number): void {
    this.processItem6(item, index);
  }
  
  private processItem6(item: string, index: number): void {
    this.processItem7(item, index);
  }
  
  private processItem7(item: string, index: number): void {
    this.processItem8(item, index);
  }
  
  private processItem8(item: string, index: number): void {
    this.processItem9(item, index);
  }
  
  private processItem9(item: string, index: number): void {
    this.processItem10(item, index);
  }
  
  private processItem10(item: string, index: number): void {
    console.log(`Selected: ${item} at ${index}`);
    this.service003.method003();
  }
  
  // 静态方法
  static createInstance(): Level1_B {
    return new Level1_B();
  }
  
  // 异步方法链
  private async fetchData(): Promise<void> {
    try {
      const data = await this.service003.fetchData();
      this.processFetchedData(data);
    } catch (error) {
      this.handleError(error);
    }
  }
  
  private processFetchedData(data: any): void {
    this.items = data;
  }
  
  private handleError(error: Error): void {
    console.error(error);
  }
  
  // 混入方法
  mixinMethod(): void {
    super.mixinMethod();
    console.log('Level1_B.mixinMethod');
  }
  
  aboutToAppear(): void {
    this.fetchData();
  }
  
  build() {
    Column() {
      List() {
        ForEach(this.items, (item: string, index: number) => {
          ListItem() {
            Text(item)
              .onClick(() => this.onItemSelected(item, index))
          }
        })
      }
    }
  }
}
