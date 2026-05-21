/**
 * 子页面A - 测试继承和方法重写
 */

import { Logger } from '../utils/Logger';
import { User } from '../models/User';

// 基础页面类
abstract struct BasePage {
  @State protected title: string = '';
  @State protected loading: boolean = false;

  abstract getPageTitle(): string;
  
  protected showLoading(): void {
    this.loading = true;
  }

  protected hideLoading(): void {
    this.loading = false;
  }

  protected logAction(action: string): void {
    Logger.info('BasePage', `Action: ${action}`);
  }
}

// 子页面A实现
@Entry
@Component
struct SubPageA extends BasePage {
  @State private users: User[] = [];
  @State private selectedUser: User | null = null;
  @State private searchQuery: string = '';

  aboutToAppear(): void {
    this.title = this.getPageTitle();
    this.loadUsers();
  }

  // 实现抽象方法
  getPageTitle(): string {
    return 'SubPage A - User Management';
  }

  // 重写父类方法
  protected showLoading(): void {
    super.showLoading();
    Logger.info('SubPageA', 'Custom loading shown');
  }

  // 加载用户列表
  private async loadUsers(): Promise<void> {
    this.showLoading();
    try {
      // 模拟API调用
      this.users = await this.fetchUsers();
      this.logAction('Users loaded');
    } finally {
      this.hideLoading();
    }
  }

  private async fetchUsers(): Promise<User[]> {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve([
          { id: '1', name: 'User 1', email: 'user1@test.com' },
          { id: '2', name: 'User 2', email: 'user2@test.com' }
        ] as User[]);
      }, 500);
    });
  }

  // 搜索功能
  private onSearch(query: string): void {
    this.searchQuery = query;
    this.filterUsers();
  }

  private filterUsers(): void {
    if (!this.searchQuery) {
      this.loadUsers();
      return;
    }
    
    const filtered = this.users.filter(u => 
      u.name.toLowerCase().includes(this.searchQuery.toLowerCase())
    );
    this.users = filtered;
  }

  // 选择用户
  private selectUser(user: User): void {
    this.selectedUser = user;
    this.logAction(`User selected: ${user.name}`);
  }

  // 删除用户
  private async deleteUser(userId: string): Promise<void> {
    this.showLoading();
    try {
      await this.performDelete(userId);
      this.users = this.users.filter(u => u.id !== userId);
      if (this.selectedUser?.id === userId) {
        this.selectedUser = null;
      }
    } finally {
      this.hideLoading();
    }
  }

  private async performDelete(userId: string): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, 300));
  }

  // 渲染用户列表
  private renderUserList(): void {
    List() {
      ForEach(this.users, (user: User) => {
        ListItem() {
          Row() {
            Text(user.name)
              .fontSize(16)
            Button('Delete')
              .onClick(() => this.deleteUser(user.id))
          }
          .onClick(() => this.selectUser(user))
        }
      })
    }
  }

  // 渲染用户详情
  private renderUserDetail(): void {
    if (!this.selectedUser) return;
    
    Column() {
      Text(this.selectedUser.name)
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
      Text(this.selectedUser.email)
        .fontSize(14)
        .fontColor('#666')
    }
  }

  build() {
    Column() {
      // 标题
      Text(this.title)
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .margin(16)

      // 搜索框
      TextInput({ placeholder: 'Search users...' })
        .onChange((value: string) => this.onSearch(value))
        .margin(16)

      // 加载状态
      if (this.loading) {
        LoadingProgress()
          .width(40)
          .height(40)
      } else {
        // 用户列表
        this.renderUserList();
        
        // 用户详情
        this.renderUserDetail();
      }
    }
    .width('100%')
    .height('100%')
  }
}
