# -*- coding: utf-8 -*-
"""
安全漏洞扫描模块
识别常见安全漏洞模式、敏感信息泄露、OWASP Top 10风险
"""

import sqlite3
import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from collections import defaultdict


class Severity(Enum):
    """漏洞严重等级"""
    CRITICAL = "critical"    # 可能导致系统被攻破
    HIGH = "high"            # 可能导致数据泄露
    MEDIUM = "medium"        # 可能导致信息泄露
    LOW = "low"              # 轻微安全问题
    INFO = "info"            # 安全建议


class VulnerabilityType(Enum):
    """漏洞类型"""
    HARDCODED_SECRET = "hardcoded_secret"      # 硬编码密钥/密码
    SQL_INJECTION = "sql_injection"            # SQL注入
    XSS = "xss"                                # 跨站脚本
    INSECURE_HTTP = "insecure_http"            # 不安全HTTP
    WEAK_CRYPTO = "weak_crypto"              # 弱加密算法
    PATH_TRAVERSAL = "path_traversal"          # 路径遍历
    COMMAND_INJECTION = "cmd_injection"        # 命令注入
    SSRF = "ssrf"                              # 服务端请求伪造
    INSECURE_DESERIALIZE = "insecure_deserialize"  # 不安全反序列化
    MISSING_AUTH = "missing_auth"              # 缺少认证
    DEBUG_CODE = "debug_code"                  # 调试代码残留
    SENSITIVE_LOG = "sensitive_log"            # 敏感信息日志


@dataclass
class Vulnerability:
    """安全漏洞"""
    id: str
    title: str
    type: str
    severity: str
    file_path: str
    line_number: int
    column: int
    code_snippet: str
    description: str
    remediation: str
    cwe_id: str                          # CWE编号
    owasp_category: str                  # OWASP分类
    references: List[str] = field(default_factory=list)
    confidence: str = "high"             # 置信度


class SecurityScanner:
    """安全扫描器"""

    # 硬编码密钥模式
    SECRET_PATTERNS = [
        {
            'name': 'API Key',
            'pattern': r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']([a-zA-Z0-9]{16,})["\']',
            'severity': Severity.CRITICAL,
            'cwe': 'CWE-798',
            'owasp': 'A07:2021',
        },
        {
            'name': 'Password',
            'pattern': r'(?:password|passwd|pwd)\s*[=:]\s*["\']([^"\']{4,})["\']',
            'severity': Severity.CRITICAL,
            'cwe': 'CWE-798',
            'owasp': 'A07:2021',
            'exclude': ['password:', 'password =', 'password=']  # 排除常见无值情况
        },
        {
            'name': 'Secret Key',
            'pattern': r'(?:secret[_-]?key|secretkey)\s*[=:]\s*["\']([a-zA-Z0-9]{16,})["\']',
            'severity': Severity.CRITICAL,
            'cwe': 'CWE-798',
            'owasp': 'A07:2021',
        },
        {
            'name': 'Token',
            'pattern': r'(?:token|access[_-]?token)\s*[=:]\s*["\']([a-zA-Z0-9]{20,})["\']',
            'severity': Severity.HIGH,
            'cwe': 'CWE-798',
            'owasp': 'A07:2021',
        },
        {
            'name': 'Private Key',
            'pattern': r'-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----',
            'severity': Severity.CRITICAL,
            'cwe': 'CWE-798',
            'owasp': 'A07:2021',
        },
        {
            'name': 'AWS Access Key',
            'pattern': r'AKIA[0-9A-Z]{16}',
            'severity': Severity.CRITICAL,
            'cwe': 'CWE-798',
            'owasp': 'A07:2021',
        },
    ]

    # SQL注入模式
    SQL_INJECTION_PATTERNS = [
        {
            'name': 'String Concatenation in SQL',
            'pattern': r'(?:execute|query|exec)\s*\(\s*["\'][^"\']*\+[^"\']*["\']',
            'severity': Severity.CRITICAL,
            'cwe': 'CWE-89',
            'owasp': 'A03:2021',
        },
        {
            'name': 'Template String in SQL',
            'pattern': r'(?:execute|query|exec)\s*\(\s*`[^`]*\$\{[^}]+\}',
            'severity': Severity.CRITICAL,
            'cwe': 'CWE-89',
            'owasp': 'A03:2021',
        },
    ]

    # XSS模式
    XSS_PATTERNS = [
        {
            'name': 'InnerHTML with User Input',
            'pattern': r'\.innerHTML\s*=\s*[^;]*(?:user|input|param|data)',
            'severity': Severity.HIGH,
            'cwe': 'CWE-79',
            'owasp': 'A03:2021',
        },
        {
            'name': 'document.write with Variable',
            'pattern': r'document\.write\s*\(\s*[^"\']*\+',
            'severity': Severity.HIGH,
            'cwe': 'CWE-79',
            'owasp': 'A03:2021',
        },
    ]

    # 弱加密模式
    WEAK_CRYPTO_PATTERNS = [
        {
            'name': 'MD5 Hash',
            'pattern': r'(?:md5|MD5)\s*\(',
            'severity': Severity.MEDIUM,
            'cwe': 'CWE-328',
            'owasp': 'A02:2021',
        },
        {
            'name': 'SHA1 Hash',
            'pattern': r'(?:sha1|SHA1)\s*\(',
            'severity': Severity.MEDIUM,
            'cwe': 'CWE-328',
            'owasp': 'A02:2021',
        },
        {
            'name': 'Weak Random',
            'pattern': r'Math\.random\s*\(',
            'severity': Severity.LOW,
            'cwe': 'CWE-338',
            'owasp': 'A02:2021',
        },
    ]

    # 路径遍历模式
    PATH_TRAVERSAL_PATTERNS = [
        {
            'name': 'Path Concatenation',
            'pattern': r'(?:readFile|writeFile|open)\s*\(\s*[^,)]*\+',
            'severity': Severity.HIGH,
            'cwe': 'CWE-22',
            'owasp': 'A01:2021',
        },
    ]

    # 调试代码模式
    DEBUG_PATTERNS = [
        {
            'name': 'Console.log',
            'pattern': r'console\.(log|debug|warn|error)\s*\(',
            'severity': Severity.INFO,
            'cwe': 'CWE-489',
            'owasp': 'A09:2021',
        },
        {
            'name': 'Debugger Statement',
            'pattern': r'\bdebugger\s*;?',
            'severity': Severity.LOW,
            'cwe': 'CWE-489',
            'owasp': 'A09:2021',
        },
    ]

    # 不安全HTTP
    INSECURE_HTTP_PATTERNS = [
        {
            'name': 'HTTP URL',
            'pattern': r'http://[^\s"\']+',
            'severity': Severity.LOW,
            'cwe': 'CWE-319',
            'owasp': 'A02:2021',
        },
    ]

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._vuln_counter = 0

    def _next_id(self) -> str:
        """生成漏洞ID"""
        self._vuln_counter += 1
        return f"VULN-{self._vuln_counter:04d}"

    def scan_all(self) -> List[Vulnerability]:
        """执行完整安全扫描"""
        vulnerabilities = []

        # 获取所有文件
        cursor = self.conn.execute("SELECT path FROM files")
        files = [row[0] for row in cursor.fetchall()]

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
            except Exception:
                continue

            # 执行各类扫描
            vulnerabilities.extend(self._scan_hardcoded_secrets(file_path, content, lines))
            vulnerabilities.extend(self._scan_sql_injection(file_path, content, lines))
            vulnerabilities.extend(self._scan_xss(file_path, content, lines))
            vulnerabilities.extend(self._scan_weak_crypto(file_path, content, lines))
            vulnerabilities.extend(self._scan_path_traversal(file_path, content, lines))
            vulnerabilities.extend(self._scan_debug_code(file_path, content, lines))
            vulnerabilities.extend(self._scan_insecure_http(file_path, content, lines))

        # 按严重等级排序
        severity_order = {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 1,
            Severity.MEDIUM.value: 2,
            Severity.LOW.value: 3,
            Severity.INFO.value: 4,
        }
        vulnerabilities.sort(key=lambda v: severity_order.get(v.severity, 99))

        return vulnerabilities

    def _scan_hardcoded_secrets(self, file_path: str, content: str,
                                 lines: List[str]) -> List[Vulnerability]:
        """扫描硬编码密钥"""
        vulnerabilities = []

        for pattern_def in self.SECRET_PATTERNS:
            for match in re.finditer(pattern_def['pattern'], content, re.IGNORECASE):
                # 检查排除项
                if 'exclude' in pattern_def:
                    matched_text = match.group(0).lower()
                    if any(exc in matched_text for exc in pattern_def['exclude']):
                        continue

                line_num = content[:match.start()].count('\n') + 1
                col = match.start() - content.rfind('\n', 0, match.start())
                code = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                # 脱敏显示
                snippet = match.group(0)
                if len(match.groups()) > 0:
                    secret = match.group(1)
                    masked = secret[:4] + '*' * (len(secret) - 8) + secret[-4:] if len(secret) > 8 else '****'
                    snippet = snippet.replace(secret, masked)

                vulnerabilities.append(Vulnerability(
                    id=self._next_id(),
                    title=f"硬编码{pattern_def['name']}",
                    type=VulnerabilityType.HARDCODED_SECRET.value,
                    severity=pattern_def['severity'].value,
                    file_path=file_path,
                    line_number=line_num,
                    column=col,
                    code_snippet=code,
                    description=f"检测到可能的硬编码{pattern_def['name']}。"
                                f"将敏感信息硬编码在源代码中会导致安全风险，"
                                f"一旦代码泄露，攻击者可直接获取这些凭证。",
                    remediation="1. 使用环境变量存储敏感信息\n"
                                "2. 使用密钥管理服务（如AWS KMS、Azure Key Vault）\n"
                                "3. 将敏感信息移至配置文件并加密\n"
                                "4. 使用.gitignore排除配置文件",
                    cwe_id=pattern_def['cwe'],
                    owasp_category=pattern_def['owasp'],
                    references=[
                        "https://cwe.mitre.org/data/definitions/798.html",
                        "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/"
                    ],
                    confidence="high"
                ))

        return vulnerabilities

    def _scan_sql_injection(self, file_path: str, content: str,
                            lines: List[str]) -> List[Vulnerability]:
        """扫描SQL注入"""
        vulnerabilities = []

        for pattern_def in self.SQL_INJECTION_PATTERNS:
            for match in re.finditer(pattern_def['pattern'], content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                col = match.start() - content.rfind('\n', 0, match.start())
                code = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                vulnerabilities.append(Vulnerability(
                    id=self._next_id(),
                    title=pattern_def['name'],
                    type=VulnerabilityType.SQL_INJECTION.value,
                    severity=pattern_def['severity'].value,
                    file_path=file_path,
                    line_number=line_num,
                    column=col,
                    code_snippet=code,
                    description="检测到可能的SQL注入漏洞。"
                                "将用户输入直接拼接到SQL查询中，"
                                "攻击者可以注入恶意SQL代码，导致数据泄露或篡改。",
                    remediation="1. 使用参数化查询（Prepared Statements）\n"
                                "2. 使用ORM框架的数据访问方法\n"
                                "3. 对用户输入进行严格验证和转义\n"
                                "4. 使用最小权限原则的数据库账户",
                    cwe_id=pattern_def['cwe'],
                    owasp_category=pattern_def['owasp'],
                    references=[
                        "https://cwe.mitre.org/data/definitions/89.html",
                        "https://owasp.org/Top10/A03_2021-Injection/"
                    ],
                    confidence="medium"
                ))

        return vulnerabilities

    def _scan_xss(self, file_path: str, content: str,
                  lines: List[str]) -> List[Vulnerability]:
        """扫描XSS漏洞"""
        vulnerabilities = []

        for pattern_def in self.XSS_PATTERNS:
            for match in re.finditer(pattern_def['pattern'], content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                col = match.start() - content.rfind('\n', 0, match.start())
                code = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                vulnerabilities.append(Vulnerability(
                    id=self._next_id(),
                    title=pattern_def['name'],
                    type=VulnerabilityType.XSS.value,
                    severity=pattern_def['severity'].value,
                    file_path=file_path,
                    line_number=line_num,
                    column=col,
                    code_snippet=code,
                    description="检测到可能的跨站脚本（XSS）漏洞。"
                                "将用户输入直接插入到DOM中，"
                                "攻击者可以注入恶意脚本，窃取用户会话或执行恶意操作。",
                    remediation="1. 使用textContent代替innerHTML\n"
                                "2. 对用户输入进行HTML转义\n"
                                "3. 使用框架提供的安全绑定（如React的{}绑定）\n"
                                "4. 实施内容安全策略（CSP）",
                    cwe_id=pattern_def['cwe'],
                    owasp_category=pattern_def['owasp'],
                    references=[
                        "https://cwe.mitre.org/data/definitions/79.html",
                        "https://owasp.org/Top10/A03_2021-Injection/"
                    ],
                    confidence="medium"
                ))

        return vulnerabilities

    def _scan_weak_crypto(self, file_path: str, content: str,
                          lines: List[str]) -> List[Vulnerability]:
        """扫描弱加密"""
        vulnerabilities = []

        for pattern_def in self.WEAK_CRYPTO_PATTERNS:
            for match in re.finditer(pattern_def['pattern'], content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                col = match.start() - content.rfind('\n', 0, match.start())
                code = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                if 'MD5' in match.group(0).upper():
                    remediation = "使用SHA-256或更强的哈希算法替代MD5"
                elif 'SHA1' in match.group(0).upper():
                    remediation = "使用SHA-256或更强的哈希算法替代SHA1"
                else:
                    remediation = "使用加密安全的随机数生成器（如crypto.getRandomValues）"

                vulnerabilities.append(Vulnerability(
                    id=self._next_id(),
                    title=pattern_def['name'],
                    type=VulnerabilityType.WEAK_CRYPTO.value,
                    severity=pattern_def['severity'].value,
                    file_path=file_path,
                    line_number=line_num,
                    column=col,
                    code_snippet=code,
                    description=f"检测到使用{pattern_def['name']}。"
                                f"该算法已被证明存在安全弱点，"
                                f"不应用于安全敏感的场景。",
                    remediation=remediation,
                    cwe_id=pattern_def['cwe'],
                    owasp_category=pattern_def['owasp'],
                    references=[
                        "https://cwe.mitre.org/data/definitions/328.html",
                        "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/"
                    ],
                    confidence="high"
                ))

        return vulnerabilities

    def _scan_path_traversal(self, file_path: str, content: str,
                             lines: List[str]) -> List[Vulnerability]:
        """扫描路径遍历"""
        vulnerabilities = []

        for pattern_def in self.PATH_TRAVERSAL_PATTERNS:
            for match in re.finditer(pattern_def['pattern'], content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                col = match.start() - content.rfind('\n', 0, match.start())
                code = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                vulnerabilities.append(Vulnerability(
                    id=self._next_id(),
                    title=pattern_def['name'],
                    type=VulnerabilityType.PATH_TRAVERSAL.value,
                    severity=pattern_def['severity'].value,
                    file_path=file_path,
                    line_number=line_num,
                    column=col,
                    code_snippet=code,
                    description="检测到可能的路径遍历漏洞。"
                                "将用户输入直接用于文件路径，"
                                "攻击者可能访问受限目录之外的文件。",
                    remediation="1. 使用路径规范化函数\n"
                                "2. 验证路径是否在允许的目录内\n"
                                "3. 使用白名单限制可访问的文件\n"
                                "4. 避免直接使用用户输入作为文件名",
                    cwe_id=pattern_def['cwe'],
                    owasp_category=pattern_def['owasp'],
                    references=[
                        "https://cwe.mitre.org/data/definitions/22.html",
                        "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"
                    ],
                    confidence="low"
                ))

        return vulnerabilities

    def _scan_debug_code(self, file_path: str, content: str,
                         lines: List[str]) -> List[Vulnerability]:
        """扫描调试代码"""
        vulnerabilities = []

        for pattern_def in self.DEBUG_PATTERNS:
            for match in re.finditer(pattern_def['pattern'], content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                col = match.start() - content.rfind('\n', 0, match.start())
                code = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                vulnerabilities.append(Vulnerability(
                    id=self._next_id(),
                    title=pattern_def['name'],
                    type=VulnerabilityType.DEBUG_CODE.value,
                    severity=pattern_def['severity'].value,
                    file_path=file_path,
                    line_number=line_num,
                    column=col,
                    code_snippet=code,
                    description=f"检测到{pattern_def['name']}。"
                                f"调试代码不应出现在生产环境中，"
                                f"可能泄露敏感信息或影响性能。",
                    remediation="1. 在构建过程中移除所有调试代码\n"
                                "2. 使用条件编译或环境变量控制调试输出\n"
                                "3. 配置代码审查流程防止提交调试代码\n"
                                "4. 使用lint规则禁止调试语句",
                    cwe_id=pattern_def['cwe'],
                    owasp_category=pattern_def['owasp'],
                    references=[
                        "https://cwe.mitre.org/data/definitions/489.html",
                        "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/"
                    ],
                    confidence="high"
                ))

        return vulnerabilities

    def _scan_insecure_http(self, file_path: str, content: str,
                            lines: List[str]) -> List[Vulnerability]:
        """扫描不安全HTTP"""
        vulnerabilities = []

        for pattern_def in self.INSECURE_HTTP_PATTERNS:
            for match in re.finditer(pattern_def['pattern'], content):
                line_num = content[:match.start()].count('\n') + 1
                col = match.start() - content.rfind('\n', 0, match.start())
                code = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                # 排除localhost
                if 'localhost' in match.group(0) or '127.0.0.1' in match.group(0):
                    continue

                vulnerabilities.append(Vulnerability(
                    id=self._next_id(),
                    title=pattern_def['name'],
                    type=VulnerabilityType.INSECURE_HTTP.value,
                    severity=pattern_def['severity'].value,
                    file_path=file_path,
                    line_number=line_num,
                    column=col,
                    code_snippet=code,
                    description="检测到使用不安全的HTTP协议。"
                                "HTTP传输的数据未加密，"
                                "可能被中间人攻击窃取或篡改。",
                    remediation="1. 将所有HTTP URL替换为HTTPS\n"
                                "2. 配置HSTS（HTTP Strict Transport Security）\n"
                                "3. 使用TLS 1.2或更高版本\n"
                                "4. 验证服务器证书",
                    cwe_id=pattern_def['cwe'],
                    owasp_category=pattern_def['owasp'],
                    references=[
                        "https://cwe.mitre.org/data/definitions/319.html",
                        "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/"
                    ],
                    confidence="high"
                ))

        return vulnerabilities

    def get_summary(self) -> Dict:
        """获取扫描摘要"""
        vulnerabilities = self.scan_all()

        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        by_file = defaultdict(int)

        for v in vulnerabilities:
            by_severity[v.severity] += 1
            by_type[v.type] += 1
            by_file[v.file_path] += 1

        # 计算风险评分
        risk_score = (
            by_severity.get(Severity.CRITICAL.value, 0) * 10 +
            by_severity.get(Severity.HIGH.value, 0) * 5 +
            by_severity.get(Severity.MEDIUM.value, 0) * 2 +
            by_severity.get(Severity.LOW.value, 0) * 1
        )

        # 安全等级
        if risk_score == 0:
            security_grade = "A"
        elif risk_score < 10:
            security_grade = "B"
        elif risk_score < 30:
            security_grade = "C"
        elif risk_score < 50:
            security_grade = "D"
        else:
            security_grade = "F"

        return {
            "total_vulnerabilities": len(vulnerabilities),
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "files_affected": len(by_file),
            "risk_score": risk_score,
            "security_grade": security_grade,
            "critical_count": by_severity.get(Severity.CRITICAL.value, 0),
            "high_count": by_severity.get(Severity.HIGH.value, 0),
        }

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def scan_security(db_path: str) -> Dict:
    """便捷函数：执行安全扫描"""
    scanner = SecurityScanner(db_path)
    try:
        vulnerabilities = scanner.scan_all()
        summary = scanner.get_summary()
        return {
            "summary": summary,
            "vulnerabilities": [
                {
                    "id": v.id,
                    "title": v.title,
                    "type": v.type,
                    "severity": v.severity,
                    "file": v.file_path,
                    "line": v.line_number,
                    "column": v.column,
                    "code": v.code_snippet,
                    "description": v.description,
                    "remediation": v.remediation,
                    "cwe": v.cwe_id,
                    "owasp": v.owasp_category,
                    "confidence": v.confidence,
                }
                for v in vulnerabilities
            ]
        }
    finally:
        scanner.close()


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python security_scanner.py <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    result = scan_security(db_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
