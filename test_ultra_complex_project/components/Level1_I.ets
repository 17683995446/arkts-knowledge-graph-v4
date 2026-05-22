/**
 * Level1_I.ets - 一级组件I
 * 拖拽排序、手势处理
 */

import { Service_012 } from '../services/Service_012';
import { Level2_J } from './Level2_J';

@Component
struct Level1_I {
  @State private draggableItems: string[] = ['A', 'B', 'C', 'D', 'E'];
  @State private draggedIndex: number = -1;
  
  private service012: Service_012 = new Service_012();
  
  // 拖拽处理链
  private handleDragStart = (index: number): void => {
    this.dragStart1(index);
  }
  
  private dragStart1(index: number): void {
    this.dragStart2(index);
  }
  
  private dragStart2(index: number): void {
    this.dragStart3(index);
  }
  
  private dragStart3(index: number): void {
    this.dragStart4(index);
  }
  
  private dragStart4(index: number): void {
    this.dragStart5(index);
  }
  
  private dragStart5(index: number): void {
    this.dragStart6(index);
  }
  
  private dragStart6(index: number): void {
    this.dragStart7(index);
  }
  
  private dragStart7(index: number): void {
    this.dragStart8(index);
  }
  
  private dragStart8(index: number): void {
    this.dragStart9(index);
  }
  
  private dragStart9(index: number): void {
    this.dragStart10(index);
  }
  
  private dragStart10(index: number): void {
    this.draggedIndex = index;
  }
  
  // 放置处理
  private handleDrop = (targetIndex: number): void => {
    this.performDrop(targetIndex);
  }
  
  private performDrop(targetIndex: number): void {
    if (this.draggedIndex === -1) return;
    
    const item = this.draggableItems[this.draggedIndex];
    this.draggableItems.splice(this.draggedIndex, 1);
    this.draggableItems.splice(targetIndex, 0, item);
    this.draggedIndex = -1;
    
    this.service012.saveOrder(this.draggableItems);
  }
  
  // 手势处理
  private handleGesture(event: GestureEvent): void {
    console.log('gesture', event);
  }
  
  build() {
    Column() {
      Level2_J()
      ForEach(this.draggableItems, (item: string, index: number) => {
        Text(item)
          .onDragStart(() => this.handleDragStart(index))
          .onDrop(() => this.handleDrop(index))
      })
    }
  }
}
