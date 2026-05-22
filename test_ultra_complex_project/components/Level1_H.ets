/**
 * Level1_H.ets - 一级组件H
 * 搜索功能、防抖处理
 */

import { Service_011 } from '../services/Service_011';
import { Util_002 } from '../utils/Util_002';
import { Level2_I } from './Level2_I';

@Component
struct Level1_H {
  @State private searchQuery: string = '';
  @State private searchResults: string[] = [];
  @State private isSearching: boolean = false;
  
  private service011: Service_011 = new Service_011();
  private util002: Util_002 = new Util_002();
  private debounceTimer: number = -1;
  
  // 搜索处理链
  private handleSearch = (query: string): void => {
    this.searchStep1(query);
  }
  
  private searchStep1(query: string): void {
    this.searchStep2(query);
  }
  
  private searchStep2(query: string): void {
    this.searchStep3(query);
  }
  
  private searchStep3(query: string): void {
    this.searchStep4(query);
  }
  
  private searchStep4(query: string): void {
    this.searchStep5(query);
  }
  
  private searchStep5(query: string): void {
    this.searchStep6(query);
  }
  
  private searchStep6(query: string): void {
    this.searchStep7(query);
  }
  
  private searchStep7(query: string): void {
    this.searchStep8(query);
  }
  
  private searchStep8(query: string): void {
    this.searchStep9(query);
  }
  
  private searchStep9(query: string): void {
    this.searchStep10(query);
  }
  
  private searchStep10(query: string): void {
    this.debouncedSearch(query);
  }
  
  private debouncedSearch(query: string): void {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.performSearch(query);
    }, 300);
  }
  
  private async performSearch(query: string): Promise<void> {
    this.isSearching = true;
    try {
      const results = await this.service011.search(query);
      this.searchResults = results;
    } finally {
      this.isSearching = false;
    }
  }
  
  // 工具方法
  private highlightMatch(text: string, query: string): string {
    return this.util002.highlight(text, query);
  }
  
  build() {
    Column() {
      Level2_I()
      TextInput({ placeholder: 'Search...' })
        .onChange(this.handleSearch)
    }
  }
}
