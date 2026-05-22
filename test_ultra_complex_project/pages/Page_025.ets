/**
 * Page_025.ets - 页面25
 * 复杂页面组件
 */

import { Level1_E } from '../components/Level1_E';
import { Service_005 } from '../services/Service_005';
import { Model_010 } from '../models/Model_010';

@Component
@Entry
struct Page_025 {
  @State private data: Model_010 = new Model_010();
  @State private loading: boolean = false;
  
  private service005: Service_005 = new Service_005();
  
  // 页面加载链
  private onPageLoad = (): void => {
    this.load1();
  }
  
  private load1(): void { this.load2(); }
  private load2(): void { this.load3(); }
  private load3(): void { this.load4(); }
  private load4(): void { this.load5(); }
  private load5(): void { this.load6(); }
  private load6(): void { this.load7(); }
  private load7(): void { this.load8(); }
  private load8(): void { this.load9(); }
  private load9(): void { this.load10(); }
  
  private load10(): void {
    this.fetchData();
  }
  
  private async fetchData(): Promise<void> {
    this.loading = true;
    try {
      const result = await this.service005.method005();
      this.data = result;
    } finally {
      this.loading = false;
    }
  }
  
  // 页面事件处理
  private handlePageEvent = (event: string): void => {
    this.event1(event);
  }
  
  private event1(e: string): void { this.event2(e); }
  private event2(e: string): void { this.event3(e); }
  private event3(e: string): void { this.event4(e); }
  private event4(e: string): void { this.event5(e); }
  private event5(e: string): void { this.event6(e); }
  private event6(e: string): void { this.event7(e); }
  private event7(e: string): void { this.event8(e); }
  private event8(e: string): void { this.event9(e); }
  private event9(e: string): void { this.event10(e); }
  
  private event10(e: string): void {
    console.log(`Page_025 event: ${e}`);
  }
  
  aboutToAppear(): void {
    this.onPageLoad();
  }
  
  onPageShow(): void {
    this.handlePageEvent('show');
  }
  
  onPageHide(): void {
    this.handlePageEvent('hide');
  }
  
  build() {
    Column() {
      Text('Page 25')
        .fontSize(24)
        .margin(20)
      
      if (this.loading) {
        LoadingProgress()
      } else {
        Level1_E()
      }
    }
    .width('100%')
    .height('100%')
  }
}
