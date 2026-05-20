/**
 * 底部操作栏组件
 */
@Component
export struct Footer {
  onLoadMore?: () => void;
  onRefresh?: () => void;
  
  private handleLoadMore(): void {
    if (this.onLoadMore) {
      this.onLoadMore();
    }
  }
  
  private handleRefresh(): void {
    if (this.onRefresh) {
      this.onRefresh();
    }
  }
  
  build() {
    Row() {
      Button('刷新')
        .onClick(() => this.handleRefresh())
        .width(100)
      
      Blank().width(20)
      
      Button('加载更多')
        .onClick(() => this.handleLoadMore())
        .width(100)
    }
    .width('100%')
    .height(60)
    .justifyContent(FlexAlign.Center)
    .backgroundColor('#fff')
  }
}
