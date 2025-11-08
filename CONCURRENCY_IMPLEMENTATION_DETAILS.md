# 并发实现详细讲解

## 概述

系统采用**三层并发控制架构**，确保高效处理同时避免资源耗尽：

1. **页面级并发**：使用 `asyncio` 异步处理单个文件内的多个页面
2. **文件级并发**：使用 `ThreadPoolExecutor` 并发处理多个文件
3. **全局并发控制**：使用 `GlobalConcurrencyController` 限制总并发数

---

## 一、页面级并发（异步并发）

### 1.1 核心实现位置

**文件**: `app/services/pdf_processor.py`  
**函数**: `_generate_explanations_async()`

### 1.2 实现机制

#### 步骤1：创建本地信号量（Semaphore）

```python
# 使用 asyncio.Semaphore 控制页面级并发数
local_semaphore = asyncio.Semaphore(max(1, concurrency))
```

**作用**：
- `concurrency` 参数控制同时处理的页面数（默认50）
- `Semaphore` 确保最多只有 `concurrency` 个页面同时调用 LLM API
- 当达到上限时，其他页面会等待，直到有页面完成

#### 步骤2：创建页面处理协程

```python
async def process_page(page_index: int) -> Tuple[int, str, Optional[Exception]]:
    # 1. 获取本地信号量（页面级并发控制）
    async with local_semaphore:
        # 2. 获取全局信号量（全局并发控制）
        if global_concurrency_controller:
            async with global_concurrency_controller:
                # 3. 调用 LLM API 生成讲解
                result = await llm_client.explain_pages_with_context(...)
```

**关键点**：
- **双重信号量控制**：
  - `local_semaphore`：限制单个文件内的页面并发数
  - `global_concurrency_controller`：限制全局总并发数
- **嵌套上下文管理器**：确保两个信号量都正确获取和释放

#### 步骤3：创建所有任务并并发执行

```python
# 为每个页面创建异步任务
tasks = [asyncio.create_task(process_page(idx)) for idx in range(total_pages)]

# 等待所有任务完成
results = await asyncio.gather(*tasks, return_exceptions=False)
```

**执行流程**：
```
页面1 ──┐
页面2 ──┤
页面3 ──┼──> asyncio.gather() ──> 等待所有完成
...     │
页面N ──┘
```

### 1.3 并发控制示例

假设有100页PDF，`concurrency=50`：

```
时间轴：
T0: 页面1-50 开始处理（获取信号量）
T1: 页面1完成，页面51开始（信号量释放后立即获取）
T2: 页面2完成，页面52开始
...
T100: 所有页面完成
```

**优势**：
- ✅ 充分利用 I/O 等待时间（LLM API 调用是异步的）
- ✅ 自动调度，无需手动管理线程
- ✅ 内存占用低（协程比线程轻量）

---

## 二、文件级并发（线程池并发）

### 2.1 核心实现位置

**文件**: `app/streamlit_app.py`  
**函数**: `_build_and_run_with_pairs()`（根据JSON重新生成）

### 2.2 实现机制

#### 步骤1：判断是否需要并发

```python
use_concurrent = total_files > 1
max_workers = min(20, total_files) if use_concurrent else 1
```

**逻辑**：
- 单个文件：顺序处理（`max_workers=1`）
- 多个文件：并发处理（最多20个线程）

#### 步骤2：创建线程池并提交任务

```python
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    # 为每个文件提交任务
    future_to_pdf = {}
    for pdf_name, pdf_bytes in pdf_data:
        future = executor.submit(
            process_single_file_from_json,
            pdf_name,
            pdf_bytes,
            on_progress,
            on_page_status
        )
        future_to_pdf[future] = pdf_name
```

**执行模型**：
```
文件1 ──┐
文件2 ──┤
文件3 ──┼──> ThreadPoolExecutor (最多20个线程)
...     │
文件N ──┘
```

#### 步骤3：收集结果（按完成顺序）

```python
for future in as_completed(future_to_pdf):
    pdf_name = future_to_pdf[future]
    result = future.result()  # 获取结果
    batch_results[pdf_name] = result
```

**特点**：
- `as_completed()` 按**完成顺序**返回，不是提交顺序
- 先完成的文件先处理结果，提高响应速度

### 2.3 为什么使用线程池而不是异步？

**原因**：
1. **Streamlit 限制**：Streamlit 的 UI 更新需要在主线程
2. **同步代码兼容**：部分处理函数是同步的（如 PDF 解析）
3. **进度回调**：需要线程安全的进度回调机制

**注意**：
- 每个线程内部仍然使用异步处理页面（通过 `asyncio.run()`）
- 线程池负责文件级并发，异步负责页面级并发

---

## 三、全局并发控制器

### 3.1 核心实现位置

**文件**: `app/services/concurrency_controller.py`  
**类**: `GlobalConcurrencyController`

### 3.2 设计目的

**问题**：文件级并发 × 页面级并发可能导致并发爆炸

**示例**：
- 10个文件 × 50个页面并发 = **500个并发请求** ❌
- 可能超过 API 限制，导致资源耗尽

**解决方案**：全局并发上限（默认200）

### 3.3 实现机制

#### 单例模式

```python
class GlobalConcurrencyController:
    _instance: Optional['GlobalConcurrencyController'] = None
    
    @classmethod
    def get_instance_sync(cls, max_global_concurrency: int = 200):
        if cls._instance is None:
            cls._instance = cls(max_global_concurrency)
        return cls._instance
```

**作用**：确保全局只有一个控制器实例

#### 信号量控制

```python
def __init__(self, max_global_concurrency: int = 200):
    self.max_global_concurrency = max_global_concurrency
    self.semaphore = asyncio.Semaphore(max_global_concurrency)
```

**工作原理**：
- 创建200个"许可证"的信号量
- 每个请求需要获取一个许可证
- 200个许可证用完时，新请求必须等待

#### 使用方式（异步上下文管理器）

```python
# 在页面处理函数中
async with global_concurrency_controller:
    # 这里会自动获取和释放信号量
    result = await llm_client.explain_pages_with_context(...)
```

**等价于**：
```python
await global_concurrency_controller.acquire()
try:
    result = await llm_client.explain_pages_with_context(...)
finally:
    global_concurrency_controller.release()
```

### 3.4 并发统计

```python
@dataclass
class ConcurrencyStats:
    current_requests: int = 0      # 当前并发数
    peak_requests: int = 0          # 峰值并发数
    total_requests: int = 0         # 总请求数
    blocked_requests: int = 0       # 被阻塞的请求数
```

**监控功能**：
- 实时查看当前并发数
- 记录峰值并发（用于性能分析）
- 统计被阻塞的请求（用于优化）

---

## 四、限流策略（Rate Limiting）

### 4.1 核心实现位置

**文件**: `app/services/gemini_client.py`  
**类**: `RateLimiter`

### 4.2 三种限制类型

1. **RPM (Requests Per Minute)**：每分钟请求数
2. **TPM (Tokens Per Minute)**：每分钟 Token 数
3. **RPD (Requests Per Day)**：每天请求数

### 4.3 智能等待策略

#### 传统方式（固定等待）

```python
# ❌ 低效：固定等待0.25秒
await asyncio.sleep(0.25)
```

#### 智能方式（动态计算）

```python
async def wait_for_slot(self, est_tokens: int) -> None:
    wait_count = 0
    base_wait = 0.1  # 基础等待时间
    max_wait = 2.0   # 最大等待时间
    
    while True:
        # 检查是否满足所有限制
        req_ok = len(self._req_timestamps) < self.max_rpm
        tpm_ok = (tokens_used + est_tokens) <= self.max_tpm
        rpd_ok = len(self._daily_requests) < self.max_rpd
        
        if req_ok and tpm_ok and rpd_ok:
            break  # 可以发送请求
        
        # 智能计算等待时间
        wait_time = base_wait
        
        # 1. RPM受限：计算到下一个可用slot的时间
        if not req_ok and self._req_timestamps:
            oldest_req = min(self._req_timestamps)
            time_until_available = self.window_seconds - (now - oldest_req)
            wait_time = min(max_wait, time_until_available / len(self._req_timestamps))
        
        # 2. TPM受限：等待时间稍长
        if not tpm_ok:
            wait_time = min(max_wait, wait_time * 1.5)
        
        # 3. 指数退避：避免频繁轮询
        if wait_count > 0:
            wait_time = min(max_wait, wait_time * (1.1 ** min(wait_count, 10)))
        
        await asyncio.sleep(wait_time)
        wait_count += 1
```

**算法优势**：
- ✅ **精确等待**：计算到下一个可用slot的精确时间
- ✅ **避免轮询**：使用指数退避减少CPU占用
- ✅ **上限保护**：最大等待2秒，避免过长等待

### 4.4 时间窗口管理

```python
# 清理过期记录（滑动窗口）
now = time.time()
self._req_timestamps = [t for t in self._req_timestamps if now - t < self.window_seconds]
self._used_tokens = [(t, n) for (t, n) in self._used_tokens if now - t < self.window_seconds]
self._daily_requests = [t for t in self._daily_requests if now - t < 86400]
```

**作用**：
- 自动清理1分钟前的请求记录（RPM/TPM）
- 自动清理24小时前的请求记录（RPD）
- 实现滑动窗口限流

---

## 五、并发控制层次结构

### 5.1 完整流程图

```
批量处理（10个文件）
│
├─ 文件1 ──> ThreadPoolExecutor (线程1)
│   │
│   ├─ 页面1 ──> asyncio.Semaphore (本地) ──> GlobalConcurrencyController ──> RateLimiter ──> LLM API
│   ├─ 页面2 ──> asyncio.Semaphore (本地) ──> GlobalConcurrencyController ──> RateLimiter ──> LLM API
│   └─ ... (最多50个页面并发)
│
├─ 文件2 ──> ThreadPoolExecutor (线程2)
│   │
│   ├─ 页面1 ──> asyncio.Semaphore (本地) ──> GlobalConcurrencyController ──> RateLimiter ──> LLM API
│   └─ ...
│
└─ ... (最多20个文件并发)
```

### 5.2 并发数计算

**理论最大并发**：
```
理论值 = 文件数 × 页面并发数
例如：10个文件 × 50个页面 = 500个并发
```

**实际最大并发**：
```
实际值 = min(理论值, 全局并发上限)
例如：min(500, 200) = 200个并发
```

**实际执行**：
- 200个请求同时进行
- 其余300个请求在 `GlobalConcurrencyController` 中等待
- 当有请求完成时，等待的请求自动开始

### 5.3 控制层次说明

| 层次 | 控制机制 | 作用范围 | 默认值 |
|------|---------|---------|--------|
| **第1层** | `RateLimiter` | API 调用 | RPM/TPM/RPD 限制 |
| **第2层** | `GlobalConcurrencyController` | 全局所有请求 | 200 |
| **第3层** | `asyncio.Semaphore` (本地) | 单个文件内的页面 | 50 |
| **第4层** | `ThreadPoolExecutor` | 多个文件 | 20 |

**执行顺序**：
1. 线程池提交文件任务
2. 文件内创建页面异步任务
3. 页面任务获取本地信号量（页面级控制）
4. 页面任务获取全局信号量（全局控制）
5. 页面任务通过限流器（API限制）
6. 调用 LLM API

---

## 六、实际运行示例

### 场景：处理3个文件，每个文件100页

**配置**：
- 页面并发：50
- 文件并发：3（顺序处理，无文件级并发）
- 全局并发上限：200

**执行过程**：

```
T0: 开始处理文件1
    ├─ 页面1-50 获取本地信号量 → 获取全局信号量 → 通过限流器 → 调用API
    └─ 页面51-100 等待本地信号量

T1: 页面1完成，释放信号量
    └─ 页面51 获取本地信号量 → 获取全局信号量 → 通过限流器 → 调用API

T2: 文件1完成，开始处理文件2
    ├─ 页面1-50 开始处理
    └─ ...

T3: 所有文件完成
```

**并发数变化**：
- T0: 50个并发（文件1的页面1-50）
- T1: 50个并发（文件1的页面51-100）
- T2: 50个并发（文件2的页面1-50）
- ...

**注意**：由于批量处理文件是顺序的，所以文件级没有并发叠加。

---

## 七、性能优化建议

### 7.1 当前瓶颈

**批量处理文件时**：
- ❌ 文件级顺序处理（`batch_process_files` 使用 for 循环）
- ✅ 页面级异步并发（性能良好）

**建议**：
- 集成 `SmartBatchHandler` 实现文件级并发
- 根据文件大小动态调整并发数

### 7.2 并发参数调优

**小文档（< 20页）**：
```python
page_concurrency = 50
file_concurrency = 5
```

**中等文档（20-100页）**：
```python
page_concurrency = 30
file_concurrency = 3
```

**大型文档（> 100页）**：
```python
page_concurrency = 20
file_concurrency = 2
```

### 7.3 监控和调试

```python
# 查看全局并发统计
from app.services.concurrency_controller import GlobalConcurrencyController

controller = GlobalConcurrencyController.get_instance_sync()
stats = controller.get_stats()

print(f"当前并发: {stats.current_requests}")
print(f"峰值并发: {stats.peak_requests}")
print(f"被阻塞请求: {stats.blocked_requests}")
```

---

## 八、总结

### 并发架构优势

1. **多层控制**：从 API 限制到全局控制，再到页面级控制
2. **自动调度**：异步机制自动管理任务调度
3. **资源保护**：全局并发上限防止资源耗尽
4. **智能限流**：动态计算等待时间，避免无效轮询

### 关键设计决策

1. **页面级使用异步**：充分利用 I/O 等待，性能最优
2. **文件级使用线程池**：兼容同步代码和 Streamlit UI
3. **全局并发控制**：防止并发爆炸，保护系统资源
4. **智能限流**：精确计算等待时间，提高效率

### 未来改进方向

1. 实现文件级并发处理（集成 `SmartBatchHandler`）
2. 动态调整全局并发限制（根据系统负载）
3. 更精细的并发控制（按文件类型、大小等）
4. 并发性能监控和可视化

