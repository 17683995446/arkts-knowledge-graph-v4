/**
 * Special_NestedCallbacks.ets - 嵌套回调组件
 * 测试深层嵌套回调
 */

@Component
struct Special_NestedCallbacks {
  private handleNestedCallbacks(): void {
    setTimeout(() => {
      setTimeout(() => {
        setTimeout(() => {
          setTimeout(() => {
            setTimeout(() => {
              console.log('deep nested timeout');
            }, 100);
          }, 100);
        }, 100);
      }, 100);
    }, 100);
  }
  
  private handlePromiseChain(): Promise<void> {
    return Promise.resolve()
      .then(() => console.log('1'))
      .then(() => console.log('2'))
      .then(() => console.log('3'))
      .then(() => console.log('4'))
      .then(() => console.log('5'));
  }
  
  build() {
    Button('Nested Callbacks')
      .onClick(() => this.handleNestedCallbacks())
  }
}
