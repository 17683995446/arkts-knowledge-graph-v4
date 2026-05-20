/**
 * 用户卡片组件
 */
import { Avatar } from './Avatar';

@Component
export struct UserCard {
  @Prop user: User;
  onClick?: () => void;
  
  private handleClick(): void {
    if (this.onClick) {
      this.onClick();
    }
  }
  
  build() {
    Row() {
      Avatar({ 
        url: this.user.avatar,
        size: 50
      })
      
      Column() {
        Text(this.user.name)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
        
        Text(this.user.email)
          .fontSize(12)
          .fontColor('#999')
      }
      .alignItems(HorizontalAlign.Start)
      .margin({ left: 10 })
      .layoutWeight(1)
    }
    .width('100%')
    .padding(15)
    .backgroundColor('#fff')
    .borderRadius(8)
    .onClick(() => this.handleClick())
  }
}

interface User {
  id: number;
  name: string;
  email: string;
  avatar?: string;
}
