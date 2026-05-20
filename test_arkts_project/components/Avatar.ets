/**
 * 头像组件
 */
@Component
export struct Avatar {
  @Prop url: string = '';
  @Prop size: number = 40;
  
  private getValidUrl(): string {
    return this.url || 'https://via.placeholder.com/150';
  }
  
  build() {
    Image(this.getValidUrl())
      .width(this.size)
      .height(this.size)
      .borderRadius(this.size / 2)
      .objectFit(ImageFit.Cover)
  }
}
