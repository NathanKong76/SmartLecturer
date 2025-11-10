# PDF讲解系统并发设计文档

## 1. 概述

本文档详细描述了PDF讲解系统中的并发架构设计，基于对实际代码的分析。该系统采用多层并发控制机制，支持文件级、页面级和全局并发管理，确保高效稳定的批量文档处理能力。

## 2. 并发架构总览

### 2.1 设计原则

- **资源保护**: 防止系统资源过载
- **API限流**: 遵守外部API的RPM、TPM、RPD限制
- **灵活配置**: 支持动态调整并发参数
- **智能调度**: 根据系统状态自动优化并发策略
- **容错机制**: 支持失败重试和优雅降级

### 2.2 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    全局并发控制器                             │
│                (GlobalConcurrencyController)                  │
│  • 单例模式 • 事件循环绑定 • 动态限流 • 统计监控               │
└─────────────────────────────────────────────────────────────┘
                                │
    ┌───────────────────────────┼───────────────────────────┐
    │                           │                           │
┌───▼───┐   ┌──────────────┐   ┌▼─────────┐   ┌─────────────┐
│验证器  │   │ 批量处理器    │   │异步处理器  │   │ 批处理器    │
│    │   │  • 同步/异步   │   │• 线程池  │   │ • 智能调度  │
└────┘   │  • 文件匹配    │   │• 批量处理 │   │ • 失败重试  │
         │  • 智能匹配    │   │• 超时处理 │   │ • 自适应   │
         └──────────────┘   └─────────┘   └─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │        缓存处理器         │
                    │     (PageLevelCache)     │
                    │  • 页面级缓存 • 命中率统计 │
                    └─────────────────────────┘
```

## 3. 全局并发控制器 (GlobalConcurrencyController)

### 3.1 核心特性

- **单例模式**: 确保全局唯一性，通过 `__new__` 和双检查锁实现
- **事件循环绑定**: 自动处理多事件循环环境下的信号量绑定
- **动态调整**: 支持运行时并发限制调整
- **统计监控**: 实时跟踪并发状态和性能指标

### 3.2 关键实现

```python
class GlobalConcurrencyController:
    _instance: Optional['GlobalConcurrencyController'] = None
    _lock = asyncio.Lock()
    _adjust_lock = asyncio.Lock()  # 序列化限制调整
    
    def _ensure_semaphore(self) -> None:
        """确保信号量绑定到当前事件循环"""
        current_loop = asyncio.get_running_loop()
        
        if self.semaphore is None or self._semaphore_loop != current_loop:
            # 处理信号量迁移
            current_used = self.stats.current_requests
            available_slots = max(0, self.max_global_concurrency - current_used)
            self.semaphore = asyncio.Semaphore(available_slots)
            self._semaphore_loop = current_loop
```

### 3.3 限流机制

- **硬限制**: 基于 `asyncio.Semaphore` 的硬性并发限制
- **监控**: 统计被阻塞的请求数，每10个阻塞警告一次
- **调整**: 支持同步和异步两种调整方式，异步方式可选择等待当前请求完成

### 3.4 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| max_global_concurrency | 200 | 全局最大并发数 |
| current_requests | 0 | 当前活跃请求数 |
| peak_requests | 0 | 历史峰值请求数 |
| blocked_requests | 0 | 被阻塞请求数 |

## 4. 并发验证器 (ConcurrencyValidator)

### 4.1 配置验证

```python
def validate_concurrency_config(
    page_concurrency: int,
    file_count: int,
    rpm_limit: int,
    tpm_budget: int,
    rpd_limit: int,
    max_global_concurrency: int = 200
) -> Tuple[bool, List[str]]
```

### 4.2 验证规则

- **全局限制检查**: `page_concurrency * file_count <= max_global_concurrency`
- **页面并发告警**: 页面并发数 > 100时警告
- **文件数量告警**: 文件数 > 10时建议分批处理
- **每日限制检查**: 预估总请求数不超过RPD限制的80%

### 4.3 智能推荐

```python
def get_concurrency_recommendations(
    file_count: int,
    avg_pages_per_file: int,
    rpm_limit: int
) -> Dict[str, Any]
```

推荐策略：
- **小负载** (< 100页): 页面并发≤50，文件并发≤5
- **中负载** (100-500页): 页面并发=30，文件并发≤3
- **大负载** (> 500页): 页面并发=20，文件并发≤2

## 5. 批量处理器系列

### 5.1 基础批量处理器 (BatchProcessor)

**文件匹配策略**:
1. 移除文件扩展名
2. 移除序号模式如 (1), (2)
3. 标准化文件名进行匹配
4. 支持多对一映射

**处理模式**:
- `batch_recompose_from_json()`: 同步批量处理
- `batch_recompose_from_json_async()`: 异步批量处理

### 5.2 批量重新生成服务 (BatchRegenerationService)

**支持三种输出模式**:
1. **PDF讲解版**: 重新合成PDF文件
2. **Markdown截图讲解**: 生成Markdown文档和截图
3. **分页HTML版**: 生成完整的分页HTML结构

**核心方法**:
```python
@staticmethod
def regenerate_pdf_batch(
    pdf_json_pairs: List[Tuple[bytes, bytes, str]],
    output_mode: str = "PDF讲解版",
    params: Dict[str, Any] = None
) -> Dict[str, Dict[str, Any]]
```

**临时文件管理**:
- 使用 `tempfile.mkdtemp()` 创建临时目录
- 自动清理机制防止磁盘空间耗尽
- ZIP文件嵌套解压避免压缩包嵌套

## 6. 异步处理器 (AsyncProcessor)

### 6.1 执行器类型

- **线程池** (`ThreadPoolExecutor`): I/O密集型任务
- **进程池** (`ProcessPoolExecutor`): CPU密集型任务

### 6.2 处理模式

**并行执行**:
```python
def execute_in_parallel(
    func: Callable,
    items: List[Any],
    show_progress: bool = True
) -> List[Any]
```

**批量更新**:
```python
def execute_with_batch_updates(
    func: Callable,
    items: List[Any],
    batch_size: int = 10
) -> Iterator[Dict[str, Any]]
```

**超时处理**:
```python
def map_with_timeout(
    func: Callable,
    items: List[Any],
    timeout: Optional[float] = None
) -> List[Any]
```

### 6.3 批处理异步处理器 (BatchAsyncProcessor)

基于 `asyncio.Queue` 的生产者-消费者模式:

```python
class BatchAsyncProcessor:
    def __init__(self, max_workers: int = 5, max_queue_size: int = 100):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.queue = asyncio.Queue(maxsize=max_queue_size)
```

**工作流程**:
1. 创建多个工作协程
2. 将任务放入队列
3. 工作者协程从队列获取任务
4. 处理完成后标记任务完成
5. 等待所有任务完成

## 7. 批处理器 (BatchHandler)

### 7.1 基础批处理器

**同步处理**:
```python
def process_batch(
    files: List,
    params: Dict[str, Any],
    on_progress: Optional[Callable] = None
) -> Dict[str, Any]
```

**并发处理**:
```python
def process_batch_concurrent(
    files: List,
    params: Dict[str, Any],
    max_workers: Optional[int] = None
) -> Dict[str, Any]
```

### 7.2 智能批处理器 (SmartBatchHandler)

**自适应并发策略**:
- **大文件** (>20MB): 限制为2个工作线程
- **中等文件** (10-20MB): 限制为3个工作线程  
- **小文件** (<10MB): 最多10个工作线程

**全局并发协调**:
```python
global_controller = GlobalConcurrencyController.get_instance_sync()
available_slots = global_controller.get_available_slots()

# 预留页面级并发槽位
estimated_pages_per_file = 50
slots_needed_per_file = min(page_concurrency, estimated_pages_per_file)
max_safe_file_workers = max(1, available_slots // max(1, slots_needed_per_file))
max_workers = min(max_workers, max_safe_file_workers)
```

**文件数量策略**:
- ≤3个文件: 顺序处理避免上下文切换开销
- >3个文件: 并发处理提高吞吐量

## 8. 缓存处理器 (PageLevelCache)

### 8.1 缓存机制

- **页面级缓存**: 避免重复处理相同页面
- **内存存储**: 基于字典的内存缓存
- **文件映射**: 支持多种文件扩展名映射
- **清理机制**: 定时清理过期缓存

### 8.2 缓存策略

- **命中率统计**: 跟踪缓存命中/未命中次数
- **大小限制**: 可配置的最大缓存条目数
- **TTL支持**: 基于时间的缓存过期

## 9. 配置管理 (AppConfig)

### 9.1 并发相关配置

```python
@dataclass
class AppConfig:
    # Rate Limiting
    concurrency: int = 50              # 页面并发数
    rpm_limit: int = 150               # 每分钟请求限制
    tpm_budget: int = 2000000          # 每分钟token预算
    rpd_limit: int = 10000             # 每日请求限制
    max_global_concurrency: int = 200  # 全局最大并发
```

### 9.2 配置验证

- **字体大小验证**: 确保在合理范围内
- **行间距验证**: 防止布局问题
- **右侧比例验证**: 确保页面布局正确
- **DPI验证**: 防止生成质量过低

## 10. 并发流程设计

### 10.1 典型处理流程

```
用户上传文件
    ↓
智能批处理器分析
    ↓
配置验证与优化
    ↓
全局并发控制器检查
    ↓
选择处理策略
    ├── 顺序处理 (小批量)
    └── 并发处理 (大批量)
    ↓
文件级并发控制
    ↓
页面级并发控制
    ↓
API限流控制
    ↓
结果汇总与缓存
    ↓
返回处理结果
```

### 10.2 错误处理与重试

**失败检测**:
- 异常捕获和状态标记
- 详细的错误信息记录
- 进度跟踪更新

**重试机制**:
- 自动重试失败的文件
- 可配置的重试次数
- 渐进式延迟重试

## 11. 性能优化策略

### 11.1 动态调优

- **系统负载感知**: 根据CPU、内存使用率调整并发数
- **API状态监控**: 根据API响应时间调整限流策略
- **自适应批处理**: 根据文件大小调整批处理参数

### 11.2 资源管理

- **连接池重用**: 避免频繁建立/断开连接
- **内存优化**: 及时释放不再需要的资源
- **临时文件清理**: 防止磁盘空间泄漏

### 11.3 监控与调试

- **实时统计**: 当前/峰值/被阻塞请求数
- **性能指标**: 处理速度、成功率统计
- **日志记录**: 详细的操作日志用于问题诊断

## 12. 配置建议

### 12.1 开发环境

```python
concurrency: int = 10         # 降低并发避免API限制
rpm_limit: int = 50           # 保守的API限制
max_global_concurrency: int = 50
```

### 12.2 生产环境

```python
concurrency: int = 50         # 平衡性能与稳定性
rpm_limit: int = 150          # 适中的API限制
max_global_concurrency: int = 200
```

### 12.3 大规模处理

```python
concurrency: int = 30         # 降低页面并发提高稳定性
rpm_limit: int = 100          # 更保守的API限制
max_global_concurrency: int = 150
# 启用分批处理避免单次过载
```

## 13. 最佳实践

### 13.1 并发设置原则

1. **小文件高并发**: 文件小、处理快，可设置较高并发
2. **大文件低并发**: 避免内存压力和API限流
3. **全局协调**: 页面并发 × 文件数量 ≤ 全局限制
4. **API友好**: 考虑RPM、TPM、RPD限制

### 13.2 错误处理

1. **优雅降级**: 超出限制时自动降低并发
2. **重试机制**: 智能重试失败的任务
3. **用户反馈**: 及时通知用户处理状态

### 13.3 监控建议

1. **实时监控**: 关注被阻塞请求数
2. **性能趋势**: 跟踪处理速度和成功率
3. **资源使用**: 监控内存和CPU使用情况

## 14. 总结

该并发设计采用多层次控制策略，从全局控制器到具体的批处理器，形成完整的并发管理生态系统。设计充分考虑了实际生产环境的需求，提供了灵活的配置选项、智能的优化策略和强大的容错机制。

**核心优势**:
- **全面性**: 覆盖文件级、页面级、全局级的完整并发控制
- **智能性**: 自动优化和自适应调整能力
- **可靠性**: 完善的错误处理和重试机制
- **可配置性**: 丰富的配置选项适应不同场景
- **可观测性**: 详细的统计和监控功能

**适用场景**:
- 批量PDF文档处理
- 大文件并发上传
- API密集型应用
- 需要高吞吐量的文档转换系统

该设计为PDF讲解系统提供了坚实的并发处理基础，确保系统在高并发场景下能够稳定、高效地运行。