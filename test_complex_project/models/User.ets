/**
 * 用户模型 - 定义用户数据结构
 */

// 用户角色枚举
enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  GUEST = 'guest',
  MODERATOR = 'moderator'
}

// 用户状态枚举
enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING = 'pending'
}

// 用户地址
interface UserAddress {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

// 用户偏好设置
interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  notifications: boolean;
  newsletter: boolean;
}

// 用户模型
interface User {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  name?: string;
  avatar?: string;
  role: UserRole;
  status: UserStatus;
  permissions?: string[];
  address?: UserAddress;
  preferences?: UserPreferences;
  phone?: string;
  createdAt?: Date;
  updatedAt?: Date;
  lastLoginAt?: Date;
}

// 用户构建器类
class UserBuilder {
  private user: Partial<User> = {
    role: UserRole.USER,
    status: UserStatus.PENDING,
    preferences: {
      theme: 'light',
      language: 'en',
      notifications: true,
      newsletter: false
    }
  };

  setId(id: string): UserBuilder {
    this.user.id = id;
    return this;
  }

  setEmail(email: string): UserBuilder {
    this.user.email = email;
    return this;
  }

  setName(firstName: string, lastName?: string): UserBuilder {
    this.user.firstName = firstName;
    this.user.lastName = lastName;
    this.user.name = lastName ? `${firstName} ${lastName}` : firstName;
    return this;
  }

  setAvatar(avatar: string): UserBuilder {
    this.user.avatar = avatar;
    return this;
  }

  setRole(role: UserRole): UserBuilder {
    this.user.role = role;
    return this;
  }

  setStatus(status: UserStatus): UserBuilder {
    this.user.status = status;
    return this;
  }

  setPermissions(permissions: string[]): UserBuilder {
    this.user.permissions = permissions;
    return this;
  }

  setAddress(address: UserAddress): UserBuilder {
    this.user.address = address;
    return this;
  }

  setPreferences(preferences: Partial<UserPreferences>): UserBuilder {
    this.user.preferences = { ...this.user.preferences, ...preferences };
    return this;
  }

  setPhone(phone: string): UserBuilder {
    this.user.phone = phone;
    return this;
  }

  build(): User {
    if (!this.user.id || !this.user.email) {
      throw new Error('User must have id and email');
    }
    
    return this.user as User;
  }
}

// 用户验证器
class UserValidator {
  static validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  static validatePhone(phone: string): boolean {
    const phoneRegex = /^\+?[\d\s-()]+$/;
    return phoneRegex.test(phone) && phone.replace(/\D/g, '').length >= 10;
  }

  static validatePassword(password: string): {
    valid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];
    
    if (password.length < 8) {
      errors.push('Password must be at least 8 characters');
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter');
    }
    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter');
    }
    if (!/\d/.test(password)) {
      errors.push('Password must contain at least one digit');
    }
    if (!/[!@#$%^&*]/.test(password)) {
      errors.push('Password must contain at least one special character');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }

  static validateUser(user: Partial<User>): {
    valid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];
    
    if (!user.email) {
      errors.push('Email is required');
    } else if (!this.validateEmail(user.email)) {
      errors.push('Invalid email format');
    }
    
    if (user.phone && !this.validatePhone(user.phone)) {
      errors.push('Invalid phone format');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
}

// 用户序列化器
class UserSerializer {
  static toJSON(user: User): string {
    return JSON.stringify(user);
  }

  static fromJSON(json: string): User {
    return JSON.parse(json) as User;
  }

  static toPlainObject(user: User): Record<string, any> {
    return {
      id: user.id,
      email: user.email,
      name: user.name,
      firstName: user.firstName,
      lastName: user.lastName,
      avatar: user.avatar,
      role: user.role,
      status: user.status,
      phone: user.phone,
      createdAt: user.createdAt?.toISOString(),
      updatedAt: user.updatedAt?.toISOString()
    };
  }
}

export { UserRole, UserStatus, UserBuilder, UserValidator, UserSerializer };
export type { User, UserAddress, UserPreferences };
