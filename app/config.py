"""
Configuration management for the application.

This module provides a centralized way to manage application configuration
from environment variables, config files, and UI inputs.
"""

from dataclasses import dataclass, field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    """Application configuration with validation."""
    
    # API Configuration
    llm_provider: str = "gemini"
    api_key: str = ""
    api_base: Optional[str] = None
    model_name: str = "gemini-2.5-pro"
    temperature: float = 0.4
    max_tokens: int = 4096
    
    # Rendering Configuration
    dpi: int = 180
    screenshot_dpi: int = 150
    right_ratio: float = 0.48
    font_size: int = 20
    line_spacing: float = 1.2
    column_padding: int = 10
    render_mode: str = "markdown"
    
    # Rate Limiting
    concurrency: int = 50
    rpm_limit: int = 150
    tpm_budget: int = 2000000
    rpd_limit: int = 10000
    
    # Prompts
    user_prompt: str = "请用中文讲解本页pdf，关键词给出英文，讲解详尽，语言简洁易懂。讲解让人一看就懂，便于快速学习。请避免不必要的换行，使页面保持紧凑。"
    context_prompt: Optional[str] = None
    use_context: bool = False
    
    # Font Configuration
    cjk_font_name: str = "SimHei"  # 字体名称，默认为黑体
    
    # Output Mode
    output_mode: str = "PDF讲解版"
    embed_images: bool = True
    markdown_title: str = "PDF文档讲解"
    
    def __post_init__(self):
        """Validate configuration values."""
        from app.services.validators import (
            validate_font_size, validate_line_spacing, 
            validate_right_ratio, validate_dpi
        )
        
        # Normalize provider string
        self.llm_provider = (self.llm_provider or "gemini").lower()
        if self.llm_provider not in ("gemini", "openai"):
            raise ValueError(f"Unsupported llm_provider: {self.llm_provider}")

        # Validate numeric parameters
        is_valid, error = validate_font_size(self.font_size)
        if not is_valid:
            raise ValueError(f"Invalid font_size in config: {error}")
        
        is_valid, error = validate_line_spacing(self.line_spacing)
        if not is_valid:
            raise ValueError(f"Invalid line_spacing in config: {error}")
        
        is_valid, error = validate_right_ratio(self.right_ratio)
        if not is_valid:
            raise ValueError(f"Invalid right_ratio in config: {error}")
        
        is_valid, error = validate_dpi(self.dpi)
        if not is_valid:
            raise ValueError(f"Invalid dpi in config: {error}")
        
        # Validate render_mode
        valid_render_modes = {"text", "markdown", "pandoc", "empty_right"}
        if self.render_mode not in valid_render_modes:
            raise ValueError(
                f"Invalid render_mode: {self.render_mode}. "
                f"Valid options: {', '.join(sorted(valid_render_modes))}"
            )

        # Validate output_mode
        valid_output_modes = {
            "PDF讲解版",
            "Markdown截图讲解",
            "HTML截图版",
            "HTML-pdf2htmlEX版",
        }
        if self.output_mode not in valid_output_modes:
            raise ValueError(
                f"Invalid output_mode: {self.output_mode}. "
                f"Valid options: {', '.join(sorted(valid_output_modes))}"
            )
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load configuration from environment variables."""
        provider = os.getenv('LLM_PROVIDER', 'gemini').lower()

        if provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY', os.getenv('API_KEY', ''))
            api_base = os.getenv('OPENAI_API_BASE', os.getenv('LLM_API_BASE', 'https://api.openai.com/v1'))
            model_name_env = os.getenv('OPENAI_MODEL_NAME')
            default_model = 'gpt-4o-mini'
        else:
            provider = 'gemini'
            api_key = os.getenv('GEMINI_API_KEY', os.getenv('API_KEY', ''))
            api_base = os.getenv('GEMINI_API_BASE', os.getenv('LLM_API_BASE', None))
            model_name_env = os.getenv('GEMINI_MODEL_NAME')
            default_model = 'gemini-2.5-pro'

        model_name = model_name_env or os.getenv('MODEL_NAME', default_model)

        return cls(
            llm_provider=provider,
            api_key=api_key,
            api_base=api_base,
            model_name=model_name,
            temperature=float(os.getenv('TEMPERATURE', '0.4')),
            max_tokens=int(os.getenv('MAX_TOKENS', '4096')),
            dpi=int(os.getenv('DPI', '180')),
            right_ratio=float(os.getenv('RIGHT_RATIO', '0.48')),
            font_size=int(os.getenv('FONT_SIZE', '20')),
            line_spacing=float(os.getenv('LINE_SPACING', '1.2')),
            render_mode=os.getenv('RENDER_MODE', 'markdown'),
            concurrency=int(os.getenv('CONCURRENCY', '50')),
            rpm_limit=int(os.getenv('RPM_LIMIT', '150')),
            tpm_budget=int(os.getenv('TPM_BUDGET', '2000000')),
            rpd_limit=int(os.getenv('RPD_LIMIT', '10000')),
        )
    
    @classmethod
    def _get_font_name_from_params(cls, params: dict) -> str:
        """从参数中获取字体名称，支持向后兼容"""
        # 优先使用 cjk_font_name
        if "cjk_font_name" in params and params["cjk_font_name"]:
            return params["cjk_font_name"]
        
        # 向后兼容：如果传入 cjk_font_path，尝试映射到字体名称
        if "cjk_font_path" in params:
            font_path = params.get("cjk_font_path", "")
            if "simhei" in font_path.lower() or "SIMHEI" in font_path:
                return "SimHei"
            elif "simsun" in font_path.lower() or "SIMSUN" in font_path:
                return "SimSun"
            elif "yahei" in font_path.lower() or "YAHEI" in font_path:
                return "Microsoft YaHei"
        
        return "SimHei"  # 默认
    
    @classmethod
    def from_params(cls, params: dict) -> 'AppConfig':
        """Create configuration from UI parameters dictionary."""
        provider = (params.get("llm_provider") or "gemini").lower()
        api_base = params.get("api_base") or None
        return cls(
            llm_provider=provider,
            api_key=params.get("api_key", ""),
            api_base=api_base,
            model_name=params.get("model_name", "gemini-2.5-pro"),
            temperature=params.get("temperature", 0.4),
            max_tokens=params.get("max_tokens", 4096),
            dpi=params.get("dpi", 180),
            screenshot_dpi=params.get("screenshot_dpi", 150),
            right_ratio=params.get("right_ratio", 0.48),
            font_size=params.get("font_size", 20),
            line_spacing=params.get("line_spacing", 1.2),
            column_padding=params.get("column_padding", 10),
            render_mode=params.get("render_mode", "markdown"),
            concurrency=params.get("concurrency", 50),
            rpm_limit=params.get("rpm_limit", 150),
            tpm_budget=params.get("tpm_budget", 2000000),
            rpd_limit=params.get("rpd_limit", 10000),
            user_prompt=params.get("user_prompt", ""),
            context_prompt=params.get("context_prompt"),
            use_context=params.get("use_context", False),
            cjk_font_name=cls._get_font_name_from_params(params),
            output_mode=params.get("output_mode", "PDF讲解版"),
            embed_images=params.get("embed_images", True),
            markdown_title=params.get("markdown_title", "PDF文档讲解"),
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for backward compatibility."""
        return {
            "llm_provider": self.llm_provider,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "dpi": self.dpi,
            "screenshot_dpi": self.screenshot_dpi,
            "right_ratio": self.right_ratio,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "column_padding": self.column_padding,
            "render_mode": self.render_mode,
            "concurrency": self.concurrency,
            "rpm_limit": self.rpm_limit,
            "tpm_budget": self.tpm_budget,
            "rpd_limit": self.rpd_limit,
            "user_prompt": self.user_prompt,
            "context_prompt": self.context_prompt,
            "use_context": self.use_context,
            "cjk_font_name": self.cjk_font_name,
            "output_mode": self.output_mode,
            "embed_images": self.embed_images,
            "markdown_title": self.markdown_title,
        }

