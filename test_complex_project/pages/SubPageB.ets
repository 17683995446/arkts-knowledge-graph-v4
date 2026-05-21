/**
 * 子页面B - 测试复杂状态管理和事件处理
 */

import { Logger } from '../utils/Logger';
import { DataProcessor } from '../utils/DataProcessor';

// 复杂状态接口
interface PageState {
  count: number;
  items: string[];
  settings: {
    autoSave: boolean;
    theme: string;
  };
}

// 事件类型
enum EventType {
  CLICK = 'click',
  CHANGE = 'change',
  SUBMIT = 'submit'
}

@Entry
@Component
struct SubPageB {
  // 复杂状态
  @State private state: PageState = {
    count: 0,
    items: [],
    settings: {
      autoSave: true,
      theme: 'light'
    }
  };

  // 计算属性
  @State private filteredItems: string[] = [];
  @State private filterText: string = '';

  // 事件处理器
  private eventHandlers: Map<EventType, Function[]> = new Map();

  aboutToAppear(): void {
    this.initializeEventHandlers();
    this.loadInitialData();
  }

  // 初始化事件处理器
  private initializeEventHandlers(): void {
    Object.values(EventType).forEach(type => {
      this.eventHandlers.set(type as EventType, []);
    });
  }

  // 注册事件监听
  private on(eventType: EventType, handler: Function): void {
    const handlers = this.eventHandlers.get(eventType) || [];
    handlers.push(handler);
    this.eventHandlers.set(eventType, handlers);
  }

  // 触发事件
  private emit(eventType: EventType, data?: any): void {
    const handlers = this.eventHandlers.get(eventType) || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (e) {
        Logger.error('SubPageB', 'Event handler error', e);
      }
    });
  }

  // 加载初始数据
  private loadInitialData(): void {
    const processor = new DataProcessor();
    this.state.items = processor.processArray(['item1', 'item2', 'item3']);
    this.updateFilteredItems();
  }

  // 计数器操作
  private increment(): void {
    this.state.count++;
    this.emit(EventType.CHANGE, { count: this.state.count });
    
    if (this.state.settings.autoSave) {
      this.saveState();
    }
  }

  private decrement(): void {
    if (this.state.count > 0) {
      this.state.count--;
      this.emit(EventType.CHANGE, { count: this.state.count });
    }
  }

  private reset(): void {
    this.state.count = 0;
    this.emit(EventType.CHANGE, { count: 0 });
  }

  // 列表操作
  private addItem(item: string): void {
    if (!item) return;
    
    this.state.items.push(item);
    this.updateFilteredItems();
    this.emit(EventType.CHANGE, { items: this.state.items });
  }

  private removeItem(index: number): void {
    if (index >= 0 && index < this.state.items.length) {
      this.state.items.splice(index, 1);
      this.updateFilteredItems();
    }
  }

  private clearItems(): void {
    this.state.items = [];
    this.filteredItems = [];
  }

  // 过滤功能
  private onFilterChange(text: string): void {
    this.filterText = text;
    this.updateFilteredItems();
  }

  private updateFilteredItems(): void {
    if (!this.filterText) {
      this.filteredItems = [...this.state.items];
    } else {
      this.filteredItems = this.state.items.filter(item =>
        item.toLowerCase().includes(this.filterText.toLowerCase())
      );
    }
  }

  // 设置操作
  private toggleAutoSave(): void {
    this.state.settings.autoSave = !this.state.settings.autoSave;
  }

  private setTheme(theme: string): void {
    this.state.settings.theme = theme;
  }

  // 保存状态
  private saveState(): void {
    Logger.info('SubPageB', 'State saved');
    // 实际保存逻辑
  }

  // 批量操作
  private batchProcess(): void {
    const processor = new DataProcessor();
    
    // 链式调用
    this.state.items = processor
      .filter(this.state.items, (item: string) => item.length > 0)
      .map((item: string) => processor.transform(item))
      .sort();
    
    this.updateFilteredItems();
  }

  // 异步操作
  private async asyncOperation(): Promise<void> {
    try {
      const result = await this.performAsyncTask();
      Logger.info('SubPageB', 'Async operation completed', result);
    } catch (e) {
      Logger.error('SubPageB', 'Async operation failed', e);
    }
  }

  private performAsyncTask(): Promise<any> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (Math.random() > 0.5) {
          resolve({ success: true });
        } else {
          reject(new Error('Random failure'));
        }
      }, 1000);
    });
  }

  // 渲染方法
  private renderCounter(): void {
    Row() {
      Button('-')
        .onClick(() => this.decrement())
      Text(`${this.state.count}`)
        .fontSize(24)
        .margin({ left: 16, right: 16 })
      Button('+')
        .onClick(() => this.increment())
    }
    .margin(16)
  }

  private renderItemList(): void {
    List() {
      ForEach(this.filteredItems, (item: string, index: number) => {
        ListItem() {
          Row() {
            Text(item)
              .fontSize(16)
            Button('X')
              .onClick(() => this.removeItem(index))
          }
          .justifyContent(FlexAlign.SpaceBetween)
          .width('100%')
        }
      })
    }
    .height(200)
  }

  private renderSettings(): void {
    Column() {
      Row() {
        Text('Auto Save')
        Toggle({ type: ToggleType.Switch, isOn: this.state.settings.autoSave })
          .onChange(() => this.toggleAutoSave())
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceBetween)

      Row() {
        Text('Theme')
        Row() {
          Button('Light')
            .onClick(() => this.setTheme('light'))
          Button('Dark')
            .onClick(() => this.setTheme('dark'))
        }
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceBetween)
    }
    .padding(16)
  }

  build() {
    Column() {
      Text('SubPage B - Complex State')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .margin(16)

      // 计数器
      this.renderCounter()

      Divider()

      // 过滤输入
      TextInput({ placeholder: 'Filter items...' })
        .onChange((value: string) => this.onFilterChange(value))
        .margin(16)

      // 项目列表
      this.renderItemList()

      // 批量操作按钮
      Row() {
        Button('Batch Process')
          .onClick(() => this.batchProcess())
        Button('Clear')
          .onClick(() => this.clearItems())
          .margin({ left: 8 })
      }
      .margin(16)

      Divider()

      // 设置
      this.renderSettings()
    }
    .width('100%')
    .height('100%')
  }
}
