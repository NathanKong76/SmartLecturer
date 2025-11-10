# 文件处理状态从 waiting 直接跳到 completed 问题分析

## 问题描述
文件处理状态会直接从 waiting 跳到 completed，跳过了 processing 状态。

## 可能原因列表

### 1. 缓存快速返回问题
**位置**: `app/ui_helpers.py:268-287`, `app/cache_processor.py:393-407`
- **问题**: 当文件有缓存且状态为 "completed" 时，`process_single_file_pdf` 会立即返回，不会触发任何进度回调（`on_progress`, `on_page_status`）
- **影响**: 虽然 `start_file` 在任务开始时被调用，但如果任务执行得非常快（从缓存返回），可能在 UI 更新之前就已经完成了，导致看起来像是从 waiting 直接跳到 completed
- **严重性**: 高

### 2. 并发处理中的时序问题
**位置**: `app/streamlit_app.py:598-614`
- **问题**: 在并发处理中，`start_file` 在提交任务前被调用，但任务可能在 `start_file` 调用和 UI 渲染之间就已经完成了
- **影响**: 状态更新可能被错过，UI 显示不准确
- **严重性**: 高

### 3. 状态更新没有强制渲染
**位置**: `app/streamlit_app.py:534-535`, `app/streamlit_app.py:604-605`
- **问题**: 在 `process_single_file_task` 中，虽然调用了 `start_file`，但没有立即强制渲染，导致状态更新可能被错过
- **影响**: UI 可能不会及时显示 processing 状态
- **严重性**: 中

### 4. 缓存返回时没有更新页面状态
**位置**: `app/ui_helpers.py:268-287`
- **问题**: 当从缓存返回时，没有调用 `on_page_status` 来更新页面状态，也没有调用 `on_progress` 来更新进度
- **影响**: 页面状态显示不准确
- **严重性**: 中

### 5. 任务执行顺序问题
**位置**: `app/streamlit_app.py:520-588`
- **问题**: 在 `process_single_file_task` 中，`start_file` 在任务内部被调用，但在并发处理中，任务可能在提交后立即开始执行，导致状态更新时序混乱
- **影响**: 状态更新可能被错过
- **严重性**: 中

### 6. 缺少状态转换验证
**位置**: `app/ui/components/detailed_progress_tracker.py:162-184`, `app/ui/components/detailed_progress_tracker.py:337-359`
- **问题**: `start_file` 和 `complete_file` 方法没有验证当前状态，可能在不正确的状态下被调用
- **影响**: 状态转换可能不正确
- **严重性**: 低

### 7. 线程安全问题
**位置**: `app/ui/components/detailed_progress_tracker.py`
- **问题**: 虽然使用了锁，但在某些情况下，状态更新可能不是原子性的
- **影响**: 状态可能不一致
- **严重性**: 低

## 修复策略

1. **确保 start_file 在任务开始前被调用并立即渲染**
2. **在缓存返回时也更新状态和进度**
3. **添加状态转换验证和日志**
4. **确保状态更新的原子性**
5. **在关键状态转换点强制渲染**

