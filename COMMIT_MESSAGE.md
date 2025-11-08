docs: 分析批量处理模块的并发实现情况

## 代码分析总结

### BatchHandler 模块状态
- `app/ui/handlers/batch_handler.py` 为预留模块，包含：
  - `BatchHandler`: 基础批量处理器（顺序/并发处理）
  - `SmartBatchHandler`: 智能批量处理器（带优化功能）
- 当前状态：**未被实际使用**，仅在 `__init__.py` 中导出

### 实际并发实现情况

#### 1. 批量处理文件（生成JSON）
- **文件级并发**: ❌ 无（顺序处理，`batch_process_files` 使用 for 循环）
- **页面级并发**: ✅ 有（异步处理，默认50并发，通过 `_generate_explanations_async`）

#### 2. 根据JSON重新生成
- **文件级并发**: ✅ 有（使用 `ThreadPoolExecutor`，最多20个文件）
- **页面级并发**: ✅ 有（HTML-pdf2htmlEX版在页面解析阶段顺序处理，但文件级并发）

### 关键发现
1. 批量生成时文件级为顺序处理，可能成为性能瓶颈
2. 页面级处理均使用异步并发，性能良好
3. `BatchHandler` 模块可考虑用于优化批量处理流程

### 建议
- 考虑将 `SmartBatchHandler` 集成到 `batch_process_files` 中
- 实现文件级并发处理以提升批量处理性能

