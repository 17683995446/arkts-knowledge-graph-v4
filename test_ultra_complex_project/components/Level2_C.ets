/**
 * Level2_C.ets - 二级组件C
 */

import { Service_005 } from '../services/Service_005';
import { Level3_C } from './Level3_C';

@Component
struct Level2_C {
  @State private items: string[] = [];
  
  private service005: Service_005 = new Service_005();
  
  private loadItems = async (): Promise<void> => {
    await this.load1();
  }
  
  private async load1(): Promise<void> { await this.load2(); }
  private async load2(): Promise<void> { await this.load3(); }
  private async load3(): Promise<void> { await this.load4(); }
  private async load4(): Promise<void> { await this.load5(); }
  private async load5(): Promise<void> { await this.load6(); }
  private async load6(): Promise<void> { await this.load7(); }
  private async load7(): Promise<void> { await this.load8(); }
  private async load8(): Promise<void> { await this.load9(); }
  private async load9(): Promise<void> { await this.load10(); }
  
  private async load10(): Promise<void> {
    this.items = await this.service005.method005();
  }
  
  aboutToAppear(): void {
    this.loadItems();
  }
  
  build() {
    Column() {
      Level3_C()
      ForEach(this.items, (item: string) => {
        Text(item)
      })
    }
  }
}
