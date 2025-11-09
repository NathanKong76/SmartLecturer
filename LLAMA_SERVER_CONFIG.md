# llama.cpp 服务器配置说明

## 问题描述

当使用本地 llama.cpp 服务器时，即使应用层设置"LLM总并发页数"为 1，仍然可能出现多个 slot 被占用，导致 KV cache 溢出的错误：

```
decode: failed to find a memory slot for batch of size 2048
failed to find free space in the KV cache
```

## 问题根源分析

### "LLM总并发页数"的设计意图

**"LLM总并发页数"应该控制全局并发页数**（所有文件的总并发页数）：
- 通过 `GlobalConcurrencyController` 实现全局并发限制
- 代码注释明确说明："This makes 'concurrency' parameter control total LLM concurrent pages across all files"
- 设计目标是：无论有多少个文件，总并发页数不超过设置的值

### 实际执行时的问题

即使设置了"LLM总并发页数" = 1，仍然可能出现多个 slot 被占用，原因如下：

1. **文件级并发未受约束**：
   - 即使全局并发为1，文件级并发仍然允许最多20个文件同时处理
   - 代码：`max_file_concurrency = min(20, file_count)`
   - 这导致多个文件几乎同时开始处理

2. **并发限制调整时机问题**：
   - 每个文件都会调用 `adjust_limit(1)` 来设置全局并发限制
   - 但多个文件几乎同时调用，不会等待之前的请求完成
   - 存在竞态条件

3. **请求到达时机**：
   - 3个文件同时处理时，每个文件都会尝试发送请求
   - 虽然全局并发限制为1，但由于竞态条件，仍然会有多个请求几乎同时到达服务器

**示例场景**：
```
设置"LLM总并发页数" = 1
上传3个文件
├─ 文件1：调用 adjust_limit(1) → 开始处理 → 发送请求
├─ 文件2：调用 adjust_limit(1) → 开始处理 → 发送请求（几乎同时）
└─ 文件3：调用 adjust_limit(1) → 开始处理 → 发送请求（几乎同时）

结果：3个请求几乎同时到达 llama.cpp 服务器，导致多个 slot 被占用
```

## 解决方案

### 方案一：配置 llama.cpp 服务器（推荐，简单有效）

通过配置 llama.cpp 服务器，将 slot 数量设置为 1，确保服务器端同一时间只处理 1 个请求。这是最简单有效的解决方案，即使应用层有多个请求到达，服务器也会排队处理。

### 方案二：应用层修复（需要修改代码）

修复文件级并发控制，确保当"LLM总并发页数" = 1 时，文件级并发也强制为 1。这需要修改代码，确保文件级并发受到全局并发限制的约束。

## 配置方法（方案一）

### 方法一：使用命令行参数启动（推荐）

在启动 llama.cpp 服务器时，添加 `--parallel 1` 参数：

```bash
# 基本启动命令
./llama-server \
    --model your-model.gguf \
    --ctx-size 4096 \
    --parallel 1 \
    --port 8000

# 完整示例（包含其他推荐参数）
./llama-server \
    --model your-model.gguf \
    --ctx-size 4096 \
    --parallel 1 \
    --cont-batching \
    --port 8000 \
    --host 0.0.0.0
```

**关键参数说明**：
- `--parallel 1`：设置并行处理的 slot 数量为 1（**最重要**）
- `--ctx-size 4096`：设置上下文窗口大小（根据你的模型和内存调整）
- `--cont-batching`：启用连续批处理（可选，提高效率）
- `--port 8000`：设置服务器端口
- `--host 0.0.0.0`：允许外部访问（本地使用可设为 127.0.0.1）

### 方法二：使用配置文件

创建配置文件 `server-config.json`：

```json
{
    "model": "your-model.gguf",
    "ctx_size": 4096,
    "parallel": 1,
    "cont_batching": true,
    "port": 8000,
    "host": "0.0.0.0"
}
```

然后使用配置文件启动：

```bash
./llama-server --config server-config.json
```

### 方法三：使用环境变量

某些 llama.cpp 实现支持环境变量配置：

```bash
# Linux/macOS
export LLAMA_PARALLEL=1
export LLAMA_CTX_SIZE=4096
./llama-server --model your-model.gguf --port 8000

# Windows PowerShell
$env:LLAMA_PARALLEL = "1"
$env:LLAMA_CTX_SIZE = "4096"
.\llama-server.exe --model your-model.gguf --port 8000
```

## 验证配置

### 1. 检查服务器日志

启动服务器后，查看日志确认 slot 数量：

```
llama_server: parallel: 1 / 1
llama_server: slots available: 1
```

### 2. 测试请求

发送测试请求，确认不会出现多个 slot 被占用：

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 3. 监控 slot 使用情况

在服务器日志中查看 slot 使用情况，确认同一时间只有 1 个 slot 在使用：

```
slot get_availabl: id  0 | task -1 | selected slot by LRU
slot launch_slot_: id  0 | task 1234 | processing task
```

## 其他相关配置

### KV Cache 大小

如果仍然出现 KV cache 溢出，可以尝试：

1. **增加上下文大小**（如果内存允许）：
   ```bash
   --ctx-size 8192  # 或更大
   ```

2. **减少批处理大小**：
   ```bash
   --batch-size 512  # 默认可能是 2048
   ```

3. **使用更小的模型**或**量化模型**（如 Q4_K_M, Q5_K_M）

### 内存优化

如果内存有限，可以：

1. **使用量化模型**（减少内存占用）
2. **限制上下文大小**（`--ctx-size`）
3. **使用 GPU offloading**（如果有 GPU）：
   ```bash
   --n-gpu-layers 35  # 将部分层放到 GPU
   ```

## 与应用配置的配合

在应用端，确保：

1. **设置并发为 1**：
   - 在 Streamlit 界面中，将"LLM总并发页数"设置为 1
   - 或通过环境变量：`CONCURRENCY=1`

2. **配置 API Base URL**：
   ```bash
   # .env 文件
   LLM_PROVIDER=openai
   OPENAI_API_BASE=http://localhost:8000/v1
   OPENAI_API_KEY=not-needed
   ```

3. **建议一次只处理 1 个文件**：
   - 虽然应用支持多文件并发，但为了确保只有 1 个请求到达服务器，建议一次只处理 1 个文件

## 常见问题

### Q: "LLM总并发页数"不是应该控制全局并发吗？为什么还会出现多个 slot？

**A**: 是的，"LLM总并发页数"确实应该控制全局并发页数。但由于以下原因，仍然可能出现多个 slot：

1. **文件级并发未受约束**：即使全局并发为1，文件级并发仍然允许最多20个文件同时处理
2. **竞态条件**：多个文件几乎同时调用 `adjust_limit(1)`，但不会等待之前的请求完成
3. **请求到达时机**：多个请求几乎同时到达服务器，虽然服务器会排队，但如果服务器配置了多个 slot，仍然会占用多个 slot

**解决方案**：配置 llama.cpp 服务器的 slot 数量为 1，这样即使有多个请求到达，服务器也会确保同一时间只处理 1 个请求。

### Q: 设置了 `--parallel 1` 仍然出现多个 slot？

**A**: 检查：
1. 是否有多个 llama.cpp 服务器实例在运行
2. 服务器是否使用了配置文件（可能覆盖了命令行参数）
3. 重启服务器确保配置生效
4. 检查服务器启动日志，确认 slot 数量

### Q: 如何确认当前 slot 数量？

**A**: 查看服务器启动日志，或使用：
```bash
curl http://localhost:8000/health  # 如果支持健康检查
```

### Q: 性能会受影响吗？

**A**: 是的，`--parallel 1` 会降低吞吐量，但可以避免 KV cache 溢出。如果内存充足，可以：
- 增加 `--ctx-size`
- 使用更高效的量化模型
- 考虑使用 GPU 加速

## 参考资源

- [llama.cpp 官方文档](https://github.com/ggerganov/llama.cpp)
- [llama-server 参数说明](https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md)

## 相关代码位置

应用端配置：
- `app/config.py`：应用配置管理
- `app/services/openai_client.py`：OpenAI 兼容客户端
- `app/services/pdf_processor.py:339-344`：全局并发限制调整
- `app/streamlit_app.py:493-506`：文件级并发处理
- `ENV_SETUP.md`：环境变量配置说明

