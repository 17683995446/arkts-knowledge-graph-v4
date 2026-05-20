/**
 * 用户详情页面
 */
import { Header } from '../components/Header';
import { Avatar } from '../components/Avatar';
import { UserService } from '../utils/UserService';
import { Logger } from '../utils/Logger';

@Entry
@Component
struct UserDetail {
  @State user: User | null = null;
  @State isLoading: boolean = true;
  
  private userService: UserService = new UserService();
  private logger: Logger = new Logger('UserDetail');
  private userId: number = 0;
  
  aboutToAppear() {
    // 从路由参数获取用户ID
    // this.userId = router.getParams()?.id || 0;
    this.loadUserDetail();
  }
  
  async loadUserDetail(): Promise<void> {
    this.isLoading = true;
    try {
      this.user = await this.userService.getUserById(this.userId);
    } catch (error) {
      this.logger.error('Failed to load user detail', error);
    } finally {
      this.isLoading = false;
    }
  }
  
  async onUpdateUser(userData: Partial<User>): Promise<void> {
    if (!this.user) return;
    
    try {
      await this.userService.updateUser(this.user.id, userData);
      this.user = { ...this.user, ...userData };
      this.logger.info('User updated successfully');
    } catch (error) {
      this.logger.error('Failed to update user', error);
    }
  }
  
  build() {
    Column() {
      Header({ title: '用户详情', showBack: true })
      
      if (this.isLoading) {
        LoadingProgress()
      } else if (this.user) {
        Column() {
          Avatar({ 
            url: this.user.avatar,
            size: 100
          })
          
          Text(this.user.name)
            .fontSize(24)
            .fontWeight(FontWeight.Bold)
          
          Text(this.user.email)
            .fontSize(16)
            .fontColor('#666')
        }
        .padding(20)
      }
    }
    .width('100%')
    .height('100%')
  }
}

interface User {
  id: number;
  name: string;
  email: string;
  avatar?: string;
}
