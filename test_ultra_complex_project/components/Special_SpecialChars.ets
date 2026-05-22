/**
 * Special_SpecialChars.ets - 特殊字符组件
 * 测试特殊字符处理
 */

@Component
struct Special_SpecialChars {
  // 特殊字符方法名
  private $method$(): void {}
  private _underscore_(): void {}
  private method123(): void {}
  
  // 中文方法名
  private 中文方法(): void {
    this.处理方法();
  }
  
  private 处理方法(): void {
    console.log('中文');
  }
  
  build() {
    Text('Special Chars')
  }
}
