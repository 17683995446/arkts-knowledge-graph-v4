/**
 * 头部导航组件
 */
@Component
export struct Header {
  @Prop title: string = '';
  @Prop showBack: boolean = false;
  
  private onBackPress(): void {
    // router.back();
  }
  
  build() {
    Row() {
      if (this.showBack) {
        Image($r('app.media.ic_back'))
          .width(24)
          .height(24)
          .onClick(() => this.onBackPress())
      }
      
      Text(this.title)
        .fontSize(18)
        .fontWeight(FontWeight.Bold)
        .layoutWeight(1)
        .textAlign(TextAlign.Center)
    }
    .width('100%')
    .height(56)
    .padding({ left: 16, right: 16 })
    .backgroundColor('#fff')
  }
}
