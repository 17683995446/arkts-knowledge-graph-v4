================================================================================
ArkTS知识图谱系统 - 性能与容错测试报告
================================================================================
测试时间: 2026-05-21 15:11:36
测试耗时: 26.18 秒

--------------------------------------------------------------------------------
测试统计
--------------------------------------------------------------------------------
  通过: 13
  失败: 0
  错误: 0
  总计: 13

--------------------------------------------------------------------------------
详细测试结果
--------------------------------------------------------------------------------

[✓] 性能测试 - 小项目（10个文件）
    状态: PASS
    elapsed_time_sec: 0.0636
    memory_used_mb: 0.0872
    peak_memory_mb: 0.1519
    start_memory_bytes: 24
    end_memory_bytes: 91457
    peak_memory_bytes: 159270
    files_parsed: 10
    classes_found: 10
    methods_found: 60

[✓] 性能测试 - 中等项目（100个文件）
    状态: PASS
    elapsed_time_sec: 0.623
    memory_used_mb: 0.4501
    peak_memory_mb: 0.5939
    start_memory_bytes: 24
    end_memory_bytes: 472033
    peak_memory_bytes: 622790
    files_parsed: 110
    classes_found: 110
    methods_found: 660

[✓] 性能测试 - 大项目（500个文件）
    状态: PASS
    elapsed_time_sec: 3.5681
    memory_used_mb: 2.1
    peak_memory_mb: 2.7577
    start_memory_bytes: 24
    end_memory_bytes: 2201984
    peak_memory_bytes: 2891628
    files_parsed: 610
    classes_found: 610
    methods_found: 3660

[✓] 性能测试 - 超大文件（10万行）
    状态: PASS
    elapsed_time_sec: 17.2169
    memory_used_mb: 10.6231
    peak_memory_mb: 84.1039
    start_memory_bytes: 24
    end_memory_bytes: 11139186
    peak_memory_bytes: 88189354
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

[✓] 容错测试 - 网络中断（AI查询）
    状态: PASS
    network_error_handled: True
    error_message: Network error: Connection reset by peer

[✓] 容错测试 - 递归深度超限
    状态: PASS
    nesting_depth: 100
    parse_time: 0.022163315000398143
    methods_found: 32

[✓] 压力测试 - 并发解析多个项目
    状态: PASS
    projects_tested: 5
    successful: 5
    failed: 0
    total_time: 0.6397747360006178
    peak_memory_mb: 0.7908353805541992

[✓] 压力测试 - 大数据量批量插入
    状态: PASS
    batch_size: 10000
    insert_time: 0.24080813099953957
    files_inserted: 10000
    classes_inserted: 10000
    methods_inserted: 10000
    insert_rate_per_sec: 124580.51094652349

[✓] 压力测试 - 长时间运行稳定性
    状态: PASS
    iterations: 10
    avg_time_sec: 0.3012
    min_time_sec: 0.2994
    max_time_sec: 0.3065
    time_variance_sec: 0.0071
    avg_memory_mb: 0.3206
    max_memory_mb: 0.3239
    stability_score: GOOD

================================================================================
测试报告结束
================================================================================