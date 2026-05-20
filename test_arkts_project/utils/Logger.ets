/**
 * 日志工具类
 */
export class Logger {
  private tag: string;
  private static level: LogLevel = LogLevel.DEBUG;
  
  constructor(tag: string) {
    this.tag = tag;
  }
  
  static setLevel(level: LogLevel): void {
    Logger.level = level;
  }
  
  debug(message: string, ...args: any[]): void {
    if (Logger.level <= LogLevel.DEBUG) {
      console.debug(`[${this.tag}] ${message}`, ...args);
    }
  }
  
  info(message: string, ...args: any[]): void {
    if (Logger.level <= LogLevel.INFO) {
      console.info(`[${this.tag}] ${message}`, ...args);
    }
  }
  
  warn(message: string, ...args: any[]): void {
    if (Logger.level <= LogLevel.WARN) {
      console.warn(`[${this.tag}] ${message}`, ...args);
    }
  }
  
  error(message: string, ...args: any[]): void {
    if (Logger.level <= LogLevel.ERROR) {
      console.error(`[${this.tag}] ${message}`, ...args);
    }
  }
}

enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}
