================================================================================
ArkTS知识图谱系统 - 性能与容错测试报告
================================================================================
测试时间: 2026-05-21 15:10:28
测试耗时: 26.50 秒

--------------------------------------------------------------------------------
测试统计
--------------------------------------------------------------------------------
  通过: 12
  失败: 0
  错误: 1
  总计: 13

--------------------------------------------------------------------------------
详细测试结果
--------------------------------------------------------------------------------

[✓] 性能测试 - 小项目（10个文件）
    状态: PASS
    elapsed_time_sec: 0.0654
    memory_used_mb: 0.0864
    peak_memory_mb: 0.1512
    start_memory_bytes: 24
    end_memory_bytes: 90616
    peak_memory_bytes: 158568
    files_parsed: 10
    classes_found: 10
    methods_found: 60

[✓] 性能测试 - 中等项目（100个文件）
    状态: PASS
    elapsed_time_sec: 0.6223
    memory_used_mb: 0.4476
    peak_memory_mb: 0.5913
    start_memory_bytes: 24
    end_memory_bytes: 469318
    peak_memory_bytes: 620035
    files_parsed: 110
    classes_found: 110
    methods_found: 660

[✓] 性能测试 - 大项目（500个文件）
    状态: PASS
    elapsed_time_sec: 3.6069
    memory_used_mb: 2.107
    peak_memory_mb: 2.7647
    start_memory_bytes: 24
    end_memory_bytes: 2209378
    peak_memory_bytes: 2899035
    files_parsed: 610
    classes_found: 610
    methods_found: 3660

[✓] 性能测试 - 超大文件（10万行）
    状态: PASS
    elapsed_time_sec: 17.3796
    memory_used_mb: 10.6255
    peak_memory_mb: 84.1027
    start_memory_bytes: 24
    end_memory_bytes: 11141616
    peak_memory_bytes: 88188098
    total_lines: 100000
    files_parsed: 1221

[✓] 容错测试 - 文件不存在
    状态: PASS
    error_handled: True
    error_message: 项目路径不存在: /non/existent/path/project

[✓] 容错测试 - 权限不足
    状态: PASS
    continued_parsing: True
    files_parsed: 5

[✓] 容错测试 - 非法字符编码
    状态: PASS
    files_tested: 5
    files_parsed: 7
    test_results: [{'file': 'utf8_bom.ets', 'status': 'created'}, {'file': 'gbk.ets', 'status': 'created'}, {'file': 'latin1.ets', 'status': 'created'}, {'file': 'binary.ets', 'status': 'created'}, {'file': 'mixed.ets', 'status': 'created'}]

[✓] 容错测试 - 数据库锁定
    状态: PASS
    concurrent_access_tested: True
    errors_caught: 0

[✗] 容错测试 - 网络中断（AI查询）
    状态: ERROR
    错误: <module 'arkts_knowledge_graph' from '/workspace/arkts-knowledge-graph-v4/arkts_knowledge_graph.py'> does not have the attribute 'OpenAI'

[✓] 容错测试 - 递归深度超限
    状态: PASS
    nesting_depth: 100
    parse_time: 0.022004851999554376
    methods_found: 32

[✓] 压力测试 - 并发解析多个项目
    状态: PASS
    projects_tested: 5
    successful: 5
    failed: 0
    total_time: 0.6458721380004135
    peak_memory_mb: 0.8082065582275391

[✓] 压力测试 - 大数据量批量插入
    状态: PASS
    batch_size: 10000
    insert_time: 0.2410426999995252
    files_inserted: 10000
    classes_inserted: 10000
    methods_inserted: 10000
    insert_rate_per_sec: 124459.2763027426

[✓] 压力测试 - 长时间运行稳定性
    状态: PASS
    iterations: 10
    avg_time_sec: 0.3091
    min_time_sec: 0.3014
    max_time_sec: 0.3307
    time_variance_sec: 0.0293
    avg_memory_mb: 0.3246
    max_memory_mb: 0.3255
    stability_score: GOOD

================================================================================
测试报告结束
================================================================================