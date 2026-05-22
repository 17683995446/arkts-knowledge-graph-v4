/**
 * Level1_G.ets - 一级组件G
 * 列表处理、分页逻辑
 */

import { Service_010 } from '../services/Service_010';
import { Model_003 } from '../models/Model_003';
import { Level2_H } from './Level2_H';

@Component
struct Level1_G {
  @State private items: Model_003[] = [];
  @State private currentPage: number = 1;
  @State private totalPages: number = 10;
  
  private service010: Service_010 = new Service_010();
  
  // 分页处理链
  private goToPage = (page: number): void => {
    this.pageNavigation1(page);
  }
  
  private pageNavigation1(page: number): void {
    this.pageNavigation2(page);
  }
  
  private pageNavigation2(page: number): void {
    this.pageNavigation3(page);
  }
  
  private pageNavigation3(page: number): void {
    this.pageNavigation4(page);
  }
  
  private pageNavigation4(page: number): void {
    this.pageNavigation5(page);
  }
  
  private pageNavigation5(page: number): void {
    this.pageNavigation6(page);
  }
  
  private pageNavigation6(page: number): void {
    this.pageNavigation7(page);
  }
  
  private pageNavigation7(page: number): void {
    this.pageNavigation8(page);
  }
  
  private pageNavigation8(page: number): void {
    this.pageNavigation9(page);
  }
  
  private pageNavigation9(page: number): void {
    this.pageNavigation10(page);
  }
  
  private pageNavigation10(page: number): void {
    this.currentPage = page;
    this.loadPageData();
  }
  
  private async loadPageData(): Promise<void> {
    const data = await this.service010.getPage(this.currentPage);
    this.items = data;
  }
  
  // 列表操作
  private sortItems(key: keyof Model_003): void {
    this.items.sort((a, b) => {
      return String(a[key]).localeCompare(String(b[key]));
    });
  }
  
  private filterItems(predicate: (item: Model_003) => boolean): void {
    this.items = this.items.filter(predicate);
  }
  
  aboutToAppear(): void {
    this.loadPageData();
  }
  
  build() {
    Column() {
      Level2_H()
      List() {
        ForEach(this.items, (item: Model_003) => {
          ListItem() {
            Text(item.toString())
          }
        })
      }
    }
  }
}
