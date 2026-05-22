/**
 * Level1_J.ets - 一级组件J
 * 模态框、对话框管理
 */

import { Service_013 } from '../services/Service_013';
import { Level3_A } from './Level3_A';

@Component
@CustomDialog
struct Level1_J {
  @State private isModalOpen: boolean = false;
  @State private modalContent: string = '';
  
  private service013: Service_013 = new Service_013();
  
  // 模态框处理链
  private openModal = (content: string): void => {
    this.modalStep1(content);
  }
  
  private modalStep1(content: string): void {
    this.modalStep2(content);
  }
  
  private modalStep2(content: string): void {
    this.modalStep3(content);
  }
  
  private modalStep3(content: string): void {
    this.modalStep4(content);
  }
  
  private modalStep4(content: string): void {
    this.modalStep5(content);
  }
  
  private modalStep5(content: string): void {
    this.modalStep6(content);
  }
  
  private modalStep6(content: string): void {
    this.modalStep7(content);
  }
  
  private modalStep7(content: string): void {
    this.modalStep8(content);
  }
  
  private modalStep8(content: string): void {
    this.modalStep9(content);
  }
  
  private modalStep9(content: string): void {
    this.modalStep10(content);
  }
  
  private modalStep10(content: string): void {
    this.modalContent = content;
    this.isModalOpen = true;
  }
  
  // 关闭处理
  private closeModal = (): void => {
    this.isModalOpen = false;
    this.service013.logModalClose();
  }
  
  // 确认处理
  private confirmModal = (): void => {
    this.service013.confirmAction();
    this.closeModal();
  }
  
  // 取消处理
  private cancelModal = (): void => {
    this.service013.cancelAction();
    this.closeModal();
  }
  
  build() {
    Column() {
      Level3_A()
      Button('Open Modal')
        .onClick(() => this.openModal('Default Content'))
      
      if (this.isModalOpen) {
        Column() {
          Text(this.modalContent)
          Button('Confirm').onClick(this.confirmModal)
          Button('Cancel').onClick(this.cancelModal)
        }
      }
    }
  }
}
