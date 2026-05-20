/**
 * 主入口页面
 * 展示用户列表和基本信息
 */
import { UserCard } from '../components/UserCard';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { UserService } from '../utils/UserService';
import { Logger } from '../utils/Logger';

@Entry
@Component
struct Index {
  // 状态变量
  @State userList: User[] = [];
  @State isLoading: boolean = false;
  @State currentPage: number = 1;
  
  // 私有变量
  private userService: UserService = new UserService();
  private logger: Logger = new Logger('Index');
  
  // 页面加载时调用
  aboutToAppear() {
    this.logger.info('Page appearing');
    this.loadUsers();
  }
  
  // 加载用户列表
  async loadUsers(): Promise<void> {
    this.isLoading = true;
    try {
      this.userList = await this.userService.fetchUsers(this.currentPage);
      this.logger.debug(`Loaded ${this.userList.length} users`);
    } catch (error) {
      this.logger.error('Failed to load users', error);
    } finally {
      this.isLoading = false;
    }
  }
  
  // 刷新数据
  async onRefresh(): Promise<void> {
    this.currentPage = 1;
    await this.loadUsers();
  }
  
  // 加载更多
  async onLoadMore(): Promise<void> {
    this.currentPage++;
    const newUsers = await this.userService.fetchUsers(this.currentPage);
    this.userList = [...this.userList, ...newUsers];
  }
  
  // 处理用户点击
  onUserClick(user: User): void {
    this.logger.info(`User clicked: ${user.name}`);
    // 导航到详情页
    // router.push({ url: '/pages/UserDetail', params: { id: user.id } });
  }
  
  // 构建UI
  build() {
    Column() {
      // 头部组件
      Header({ title: '用户列表' })
      
      // 内容区域
      if (this.isLoading) {
        LoadingProgress()
          .width(50)
          .height(50)
      } else {
        List() {
          ForEach(this.userList, (user: User) => {
            ListItem() {
              UserCard({ 
                user: user,
                onClick: () => this.onUserClick(user)
              })
            }
          })
        }
        .width('100%')
        .layoutWeight(1)
      }
      
      // 底部组件
      Footer({ 
        onLoadMore: () => this.onLoadMore(),
        onRefresh: () => this.onRefresh()
      })
    }
    .width('100%')
    .height('100%')
  }
}

// 用户接口定义
interface User {
  id: number;
  name: string;
  email: string;
  avatar?: string;
}
