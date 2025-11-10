# ScriptRunContext 警告问题分析

## 问题描述
在运行 Streamlit 应用时，出现以下警告：
```
Thread 'ThreadPoolExecutor-2_0': missing ScriptRunContext! This warning can be ignored when running in bare mode.
Thread 'ThreadPoolExecutor-2_1': missing ScriptRunContext! This warning can be ignored when running in bare mode.
```

## 可能导致问题的原因

### 1. **detailed_progress_tracker.py 中的渲染问题**
- **位置**: `app/ui/components/detailed_progress_tracker.py`
- **问题**: `_do_render()` 方法虽然检查了 ScriptRunContext，但在某些情况下可能仍然会触发警告
- **具体问题**:
  - `render_overview()` 和 `render_details()` 中直接使用 `st.progress()`, `st.metric()`, `st.info()` 等 Streamlit 函数
  - 即使检查了 ScriptRunContext，如果检查时机不对，仍可能触发警告
  - `st.session_state` 的访问可能触发上下文检查

### 2. **safe_html_renderer.py 中的 Streamlit 环境检测**
- **位置**: `app/services/safe_html_renderer.py`
- **问题**: 在后台线程中检测 Streamlit 环境时，`hasattr(st, 'runtime') and st.runtime.exists()` 可能触发 ScriptRunContext 检查
- **具体问题**:
  - 第 23 行：`streamlit_env = hasattr(st, 'runtime') and st.runtime.exists()`
  - 这个检查在后台线程中执行时，会触发 Streamlit 的上下文检查

### 3. **StateManager 类在后台线程中的使用**
- **位置**: `app/ui_helpers.py`
- **问题**: `StateManager` 的方法直接访问 `st.session_state`，在后台线程中调用时会触发警告
- **具体问题**:
  - `get_batch_results()` 和 `set_batch_results()` 直接访问 `st.session_state`
  - 在 `process_single_file_task` 中，后台线程可能调用这些方法

### 4. **html_renderer.py 中的 Streamlit 检测**
- **位置**: `app/services/html_renderer.py`
- **问题**: 在错误处理中检测 Streamlit 环境，可能在后台线程中触发
- **具体问题**:
  - 第 183 行：`if hasattr(st, 'runtime') and st.runtime.exists()`
  - 这个检查在后台线程中可能触发警告

### 5. **create_thread_safe_callbacks 中的间接访问**
- **位置**: `app/ui/components/detailed_progress_tracker.py`
- **问题**: 虽然回调函数本身不直接访问 Streamlit，但 `update_file_page_progress` 和 `update_page_status` 可能间接触发
- **具体问题**:
  - 回调函数调用 `update_file_page_progress` 和 `update_page_status`
  - 这些方法虽然使用了锁，但可能在某些情况下仍然触发 Streamlit 上下文检查

## 修复策略

1. **增强 ScriptRunContext 检查**：在所有可能被后台线程调用的地方，添加更严格的检查
2. **避免在后台线程中访问 Streamlit**：使用线程安全的数据结构，只在主线程中更新 UI
3. **改进 Streamlit 环境检测**：使用更安全的方式检测 Streamlit 环境，避免触发上下文检查
4. **使用队列机制**：在后台线程中收集更新，在主线程中批量应用

