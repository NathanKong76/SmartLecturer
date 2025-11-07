"""
Sidebar Component.

Renders the sidebar configuration form with modular sections.
"""

from typing import Dict, Any, List
import streamlit as st


class SidebarForm:
    """Modular sidebar form with sections."""

    def __init__(self):
        """Initialize sidebar form."""
        pass

    def render(self) -> Dict[str, Any]:
        """
        Render complete sidebar form.

        Returns:
            Dictionary of form parameters
        """
        with st.sidebar:
            st.header("⚙️ 参数配置")

            # API Configuration Section
            api_params = self._render_api_section()

            # Rendering Configuration Section
            render_params = self._render_rendering_section()

            # Output Mode Section
            output_params = self._render_output_section()

            # Context Enhancement Section
            context_params = self._render_context_section()

            # Combine all parameters
            params = {
                **api_params,
                **render_params,
                **output_params,
                **context_params
            }

            return params

    def _render_api_section(self) -> Dict[str, Any]:
        """Render API configuration section."""

        st.subheader("🔑 API 配置")

        import os

        provider_options = ["Gemini", "OpenAI"]
        env_provider = os.getenv('LLM_PROVIDER', 'gemini').lower()
        default_provider_index = 1 if env_provider == 'openai' else 0
        provider_label = st.radio(
            "LLM 提供方",
            provider_options,
            index=default_provider_index,
            key="sidebar_llm_provider"
        )
        llm_provider = 'openai' if provider_label == "OpenAI" else 'gemini'

        if llm_provider == 'openai':
            default_api_key = os.getenv('OPENAI_API_KEY', os.getenv('API_KEY', ''))
            api_key_help = "您的 OpenAI API 密钥"
            default_model = os.getenv('OPENAI_MODEL_NAME', os.getenv('MODEL_NAME', 'gpt-4o-mini'))
            model_help = "使用的 OpenAI 模型"
            api_base_default = os.getenv('OPENAI_API_BASE', os.getenv('LLM_API_BASE', 'https://api.openai.com/v1')) or ""
            api_base_input = st.text_input(
                "API Base URL",
                value=api_base_default,
                help="OpenAI 兼容接口基础地址，可根据需要修改。",
                key="sidebar_llm_api_base"
            )
            api_base = api_base_input.strip() or None
        else:
            default_api_key = os.getenv('GEMINI_API_KEY', os.getenv('API_KEY', ''))
            api_key_help = "您的 Gemini API 密钥"
            default_model = os.getenv('GEMINI_MODEL_NAME', os.getenv('MODEL_NAME', 'gemini-2.5-pro'))
            model_help = "使用的 Gemini 模型"
            api_base_env = os.getenv('GEMINI_API_BASE', os.getenv('LLM_API_BASE', ''))
            api_base = (api_base_env.strip() if api_base_env else None)
            st.session_state.setdefault("sidebar_llm_api_base", api_base or "")

        api_key = st.text_input(
            "API Key",
            value=default_api_key,
            type="password",
            help=api_key_help,
            key="sidebar_llm_api_key"
        )

        model_name = st.text_input(
            "模型名称",
            value=default_model,
            help=model_help,
            key="sidebar_llm_model_name"
        )

        col1, col2 = st.columns(2)

        with col1:
            temperature = st.slider(
                "温度",
                0.0, 1.0, 0.4, 0.1,
                help="控制输出随机性"
            )

        with col2:
            max_tokens = st.number_input(
                "最大输出 Tokens",
                min_value=256,
                max_value=8192,
                value=4096,
                step=256,
                help="限制单次响应长度"
            )

        st.divider()

        return {
            "llm_provider": llm_provider,
            "api_key": api_key,
            "api_base": api_base,
            "model_name": model_name,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens)
        }

    def _render_rendering_section(self) -> Dict[str, Any]:
        """Render rendering configuration section."""
        st.subheader("🎨 渲染配置")

        # PDF Rendering
        col1, col2 = st.columns(2)

        with col1:
            dpi = st.number_input(
                "渲染DPI (仅供LLM)",
                min_value=96,
                max_value=300,
                value=180,
                step=12,
                help="页面渲染质量，越高越清晰但越慢"
            )

        with col2:
            right_ratio = st.slider(
                "右侧留白比例",
                0.2, 0.6, 0.48, 0.01,
                help="右侧讲解区域占页面宽度比例"
            )

        # Typography
        col1, col2 = st.columns(2)

        with col1:
            font_size = st.number_input(
                "右栏字体大小",
                min_value=8,
                max_value=20,
                value=20,
                step=1,
                help="讲解文字的字体大小"
            )

        with col2:
            line_spacing = st.slider(
                "讲解文本行距",
                0.6, 2.0, 1.2, 0.1,
                help="行与行之间的距离"
            )

        col1, col2 = st.columns(2)

        with col1:
            column_padding = st.slider(
                "栏内边距",
                2, 16, 10, 1,
                help="控制每栏左右内边距"
            )

        with col2:
            concurrency = st.slider(
                "并发页数",
                1, 100, 50, 1,
                help="同时处理的页面数量"
            )

        # Rate Limits
        col1, col2 = st.columns(2)

        with col1:
            rpm_limit = st.number_input(
                "RPM 上限",
                min_value=10,
                max_value=5000,
                value=150,
                step=10,
                help="每分钟请求数限制"
            )

        with col2:
            tpm_budget = st.number_input(
                "TPM 预算",
                min_value=100000,
                max_value=20000000,
                value=2000000,
                step=100000,
                help="每分钟 Token 预算"
            )

        rpd_limit = st.number_input(
            "RPD 上限 (请求/天)",
            min_value=100,
            max_value=100000,
            value=10000,
            step=100,
            help="每天请求数限制"
        )

        # Prompt
        user_prompt = st.text_area(
            "讲解风格/要求",
            value="请用中文讲解本页pdf，关键词给出英文，讲解详尽，语言简洁易懂。讲解让人一看就懂，便于快速学习。请避免不必要的换行，使页面保持紧凑。",
            help="自定义讲解提示词"
        )

        # Font selection
        cjk_font_name = self._render_font_selection()

        # Render mode
        render_mode = st.selectbox(
            "右栏渲染方式",
            ["text", "markdown", "pandoc"],
            index=1,
            help="text: 普通文本\nmarkdown: Markdown渲染\npandoc: 高质量PDF (需Pandoc)"
        )

        st.divider()

        return {
            "dpi": int(dpi),
            "right_ratio": float(right_ratio),
            "font_size": int(font_size),
            "line_spacing": float(line_spacing),
            "column_padding": int(column_padding),
            "concurrency": int(concurrency),
            "rpm_limit": int(rpm_limit),
            "tpm_budget": int(tpm_budget),
            "rpd_limit": int(rpd_limit),
            "user_prompt": user_prompt.strip(),
            "cjk_font_name": cjk_font_name,
            "render_mode": render_mode
        }

    def _render_font_selection(self) -> str:
        """Render font selection dropdown."""
        try:
            from app.services.font_helper import get_windows_cjk_fonts
            available_fonts = get_windows_cjk_fonts()
            font_options = [font[0] for font in available_fonts]

            # Try to find SimHei
            try:
                default_index = font_options.index("SimHei")
            except ValueError:
                default_index = 0

            cjk_font_name = st.selectbox(
                "CJK 字体",
                font_options,
                index=default_index,
                help="选择用于显示中文的字体"
            )
        except Exception as e:
            st.warning(f"无法检测系统字体: {e}")
            cjk_font_name = "SimHei"

        return cjk_font_name

    def _render_output_section(self) -> Dict[str, Any]:
        """Render output mode selection section."""
        st.subheader("📤 输出模式")

        output_mode = st.radio(
            "选择输出格式",
            ["PDF讲解版", "Markdown截图讲解"],
            help="PDF讲解版：在PDF右侧添加讲解\nMarkdown截图：生成Markdown文档"
        )

        # Markdown-specific parameters
        if output_mode == "Markdown截图讲解":
            st.markdown("📝 **Markdown 参数**")

            screenshot_dpi = st.slider(
                "截图DPI",
                72, 300, 150, 12,
                help="截图质量，越高越清晰但文件越大"
            )

            embed_images = st.checkbox(
                "嵌入图片到Markdown",
                value=False,
                help="将截图编码到markdown文件，否则使用外部图片"
            )

            markdown_title = st.text_input(
                "文档标题",
                value="PDF文档讲解",
                help="生成的Markdown文档标题"
            )
        else:
            screenshot_dpi = 150
            embed_images = True
            markdown_title = "PDF文档讲解"

        st.divider()

        return {
            "output_mode": output_mode,
            "screenshot_dpi": int(screenshot_dpi),
            "embed_images": bool(embed_images),
            "markdown_title": markdown_title
        }

    def _render_context_section(self) -> Dict[str, Any]:
        """Render context enhancement section."""
        st.subheader("🧠 上下文增强")

        use_context = st.checkbox(
            "启用前后各1页上下文",
            value=False,
            help="启用后，LLM将看到前一页、当前页和后一页，提高讲解连贯性。会增加API成本。"
        )

        context_prompt = None
        if use_context:
            context_prompt = st.text_area(
                "上下文提示词",
                value="你将看到前一页、当前页和后一页的内容。请结合上下文信息，生成连贯的讲解。当前页是重点讲解页面。",
                help="指导LLM如何处理多页内容",
                disabled=False
            )
        else:
            # Show disabled field
            st.text_area(
                "上下文提示词",
                value="你将看到前一页、当前页和后一页的内容。请结合上下文信息，生成连贯的讲解。当前页是重点讲解页面。",
                help="指导LLM如何处理多页内容",
                disabled=True
            )

        st.divider()

        return {
            "use_context": bool(use_context),
            "context_prompt": context_prompt.strip() if context_prompt else None
        }


class CollapsibleSidebar:
    """Collapsible sidebar for better space utilization."""

    def __init__(self):
        """Initialize collapsible sidebar."""
        self.collapsed = False

    def render(self, content_func) -> Dict[str, Any]:
        """
        Render collapsible sidebar.

        Args:
            content_func: Function to render sidebar content

        Returns:
            Parameters dictionary
        """
        # Toggle button
        col1, col2 = st.columns([1, 4])

        with col1:
            if st.button("📋" if not self.collapsed else "📖"):
                self.collapsed = not self.collapsed

        with col2:
            st.markdown("**配置面板**")

        if not self.collapsed:
            return content_func()
        else:
            # Minimal mode - just API key
            with st.sidebar:
                st.markdown("### 快速设置")
                api_key = st.text_input(
                    "API Key",
                    type="password",
                    key="quick_api_key"
                )
                st.markdown("点击 📋 展开完整配置")
                return {
                    "llm_provider": 'gemini',
                    "api_key": api_key,
                    "api_base": None
                }
