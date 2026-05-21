/**
 * 日志工具类 - 静态方法测试
 * 包含多种日志级别和格式化功能
 */

// 日志级别枚举
enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  FATAL = 4
}

// 日志配置接口
interface LoggerConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableFile: boolean;
  filePath?: string;
}

// 日志条目接口
interface LogEntry {
  timestamp: Date;
  level: LogLevel;
  tag: string;
  message: string;
  data?: any;
}

class Logger {
  // 静态配置
  private static config: LoggerConfig = {
    level: LogLevel.INFO,
    enableConsole: true,
    enableFile: false
  };

  // 静态日志存储
  private static logs: LogEntry[] = [];
  private static maxLogs: number = 1000;

  // 配置方法
  static setConfig(config: Partial<LoggerConfig>): void {
    Logger.config = { ...Logger.config, ...config };
  }

  static getConfig(): LoggerConfig {
    return { ...Logger.config };
  }

  // 核心日志方法
  private static log(level: LogLevel, tag: string, message: string, data?: any): void {
    if (level < Logger.config.level) return;

    const entry: LogEntry = {
      timestamp: new Date(),
      level,
      tag,
      message,
      data
    };

    // 存储日志
    Logger.logs.push(entry);
    if (Logger.logs.length > Logger.maxLogs) {
      Logger.logs.shift();
    }

    // 输出到控制台
    if (Logger.config.enableConsole) {
      Logger.outputToConsole(entry);
    }

    // 输出到文件
    if (Logger.config.enableFile && Logger.config.filePath) {
      Logger.outputToFile(entry);
    }
  }

  // 控制台输出
  private static outputToConsole(entry: LogEntry): void {
    const levelStr = LogLevel[entry.level];
    const timeStr = entry.timestamp.toISOString();
    const output = `[${timeStr}] [${levelStr}] [${entry.tag}] ${entry.message}`;

    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(output, entry.data || '');
        break;
      case LogLevel.INFO:
        console.info(output, entry.data || '');
        break;
      case LogLevel.WARN:
        console.warn(output, entry.data || '');
        break;
      case LogLevel.ERROR:
      case LogLevel.FATAL:
        console.error(output, entry.data || '');
        break;
    }
  }

  // 文件输出
  private static outputToFile(entry: LogEntry): void {
    // 文件输出逻辑
  }

  // 公共日志方法
  static debug(tag: string, message: string, data?: any): void {
    Logger.log(LogLevel.DEBUG, tag, message, data);
  }

  static info(tag: string, message: string, data?: any): void {
    Logger.log(LogLevel.INFO, tag, message, data);
  }

  static warn(tag: string, message: string, data?: any): void {
    Logger.log(LogLevel.WARN, tag, message, data);
  }

  static error(tag: string, message: string, data?: any): void {
    Logger.log(LogLevel.ERROR, tag, message, data);
  }

  static fatal(tag: string, message: string, data?: any): void {
    Logger.log(LogLevel.FATAL, tag, message, data);
  }

  // 日志管理
  static clear(): void {
    Logger.logs = [];
  }

  static getLogs(): LogEntry[] {
    return [...Logger.logs];
  }

  static getLogsByLevel(level: LogLevel): LogEntry[] {
    return Logger.logs.filter(log => log.level === level);
  }

  static getLogsByTag(tag: string): LogEntry[] {
    return Logger.logs.filter(log => log.tag === tag);
  }

  // 格式化工具
  static formatObject(obj: any): string {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  }

  static formatError(error: Error): string {
    return `${error.name}: ${error.message}\n${error.stack}`;
  }

  // 性能日志
  static time(label: string): void {
    console.time(label);
  }

  static timeEnd(label: string): void {
    console.timeEnd(label);
  }

  // 分组日志
  static group(label: string): void {
    console.group(label);
  }

  static groupEnd(): void {
    console.groupEnd();
  }
}

// 导出
export { Logger, LogLevel };
export type { LoggerConfig, LogEntry };
