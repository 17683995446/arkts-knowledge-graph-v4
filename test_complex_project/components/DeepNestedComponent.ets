/**
 * 深层嵌套组件 - 测试5层+嵌套结构
 * 包含多层组件嵌套、条件渲染、循环渲染等
 */

import { BaseComponent } from './BaseComponent';

// 第一层嵌套
@Component
struct Level1Component {
  @State level: number = 1;

  build() {
    Column() {
      Text(`Level ${this.level}`)
        .fontSize(20)
      // 第二层
      Level2Component()
    }
  }
}

// 第二层嵌套
@Component
struct Level2Component {
  @State level: number = 2;
  @State items: string[] = ['a', 'b', 'c'];

  build() {
    Row() {
      Text(`Level ${this.level}`)
      // 第三层 - 循环渲染
      ForEach(this.items, (item: string) => {
        Level3Component({ item: item })
      })
    }
  }
}

// 第三层嵌套
@Component
struct Level3Component {
  @Prop item: string;
  @State showDetail: boolean = false;

  build() {
    Stack() {
      Text(this.item)
      // 条件渲染
      if (this.showDetail) {
        Level4Component()
      }
      // 第四层
      Level4Component()
    }
    .onClick(() => {
      this.showDetail = !this.showDetail;
    })
  }
}

// 第四层嵌套
@Component
struct Level4Component {
  @State level: number = 4;

  build() {
    Grid() {
      GridItem() {
        // 第五层
        Level5Component()
      }
      GridItem() {
        Level5Component()
      }
    }
  }
}

// 第五层嵌套
@Component
struct Level5Component {
  @State level: number = 5;
  @State deepData: Record<string, any> = {};

  aboutToAppear(): void {
    this.loadDeepData();
  }

  private loadDeepData(): void {
    // 多层嵌套的数据访问
    this.deepData = {
      level1: {
        level2: {
          level3: {
            level4: {
              level5: 'deep value'
            }
          }
        }
      }
    };
  }

  private getDeepValue(): string {
    // 深层属性访问链
    return this.deepData?.level1?.level2?.level3?.level4?.level5 || '';
  }

  build() {
    Column() {
      Text(`Level ${this.level}`)
        .fontSize(12)
      Text(this.getDeepValue())
        .fontSize(10)
      // 第六层 - 更深层
      Level6Component()
    }
  }
}

// 第六层嵌套 - 极限测试
@Component
struct Level6Component {
  @State level: number = 6;

  // 箭头函数嵌套
  nestedArrow = () => {
    const inner1 = () => {
      const inner2 = () => {
        const inner3 = () => {
          return this.level;
        };
        return inner3();
      };
      return inner2();
    };
    return inner1();
  };

  build() {
    Text(`Deep Level ${this.nestedArrow()}`)
      .fontSize(8)
  }
}

// 主组件 - 入口
@Entry
@Component
struct DeepNestedComponent {
  @State rootData: string = 'Root';

  build() {
    Column() {
      Text(this.rootData)
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
      // 开始深层嵌套
      Level1Component()
    }
    .width('100%')
    .height('100%')
  }
}
