# API功能测试报告

**测试时间**: 2025-09-11T15:04:37.053726

**API基础URL**: https://t8jhz8li6e.execute-api.us-east-1.amazonaws.com/legacy

## 测试摘要

- **总测试数**: 10
- **通过**: 1 (10.0%)
- **失败**: 9 (90.0%)

## 测试详情

| 端点 | 方法 | 状态码 | 响应时间 | 结果 |
|------|------|--------|----------|------|
| /health | GET | 200 | 640.31ms | ✅ PASSED |
| /presentations | GET | 403 | 618.26ms | ❌ FAILED |
| /presentations | POST | 403 | 711.18ms | ❌ FAILED |
| /presentations/test-id-123/status | GET | 403 | 635.57ms | ❌ FAILED |
| /tasks/test-task-123 | GET | 403 | 645.64ms | ❌ FAILED |
| /presentations/test-id-123/slides/1 | PUT | 403 | 617.59ms | ❌ FAILED |
| /presentations/test-id-123/download | GET | 403 | 630.98ms | ❌ FAILED |
| /outline | POST | 403 | 660.10ms | ❌ FAILED |
| /content | POST | 403 | 625.95ms | ❌ FAILED |
| /images/generate | POST | 403 | 613.61ms | ❌ FAILED |

## 错误详情

- **/presentations**: 期望状态码 [200], 实际 403
- **/presentations**: 期望状态码 [200, 201, 202], 实际 403
- **/presentations/test-id-123/status**: 期望状态码 [200, 404], 实际 403
- **/tasks/test-task-123**: 期望状态码 [200, 404], 实际 403
- **/presentations/test-id-123/slides/1**: 期望状态码 [200, 404], 实际 403
- **/presentations/test-id-123/download**: 期望状态码 [200, 404], 实际 403
- **/outline**: 期望状态码 [200, 201], 实际 403
- **/content**: 期望状态码 [200, 201], 实际 403
- **/images/generate**: 期望状态码 [200, 201], 实际 403

## 性能统计

- **平均响应时间**: 639.92ms
- **最快响应**: 613.61ms
- **最慢响应**: 711.18ms
