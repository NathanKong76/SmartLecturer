"""
Concurrency Configuration Validator.

Validates concurrency settings and provides warnings for potentially problematic configurations.
"""

from typing import Dict, Any, List, Tuple
from .logger import get_logger

logger = get_logger()


def validate_concurrency_config(
    page_concurrency: int,
    file_count: int,
    rpm_limit: int,
    tpm_budget: int,
    rpd_limit: int,
    max_global_concurrency: int = 200
) -> Tuple[bool, List[str]]:
    """
    Validate concurrency configuration and return warnings.
    
    Args:
        page_concurrency: Page-level concurrency
        file_count: Number of files being processed
        rpm_limit: API RPM limit
        tpm_budget: API TPM budget
        rpd_limit: API RPD limit
        max_global_concurrency: Maximum global concurrency limit
        
    Returns:
        Tuple of (is_valid, warnings_list)
    """
    warnings = []
    is_valid = True
    
    # Calculate theoretical maximum concurrent requests
    theoretical_max = page_concurrency * file_count
    
    # Check against global concurrency limit
    if theoretical_max > max_global_concurrency:
        warnings.append(
            f"理论最大并发数 ({theoretical_max}) 超过全局限制 ({max_global_concurrency})。"
            f"实际并发将被限制为 {max_global_concurrency}。"
        )
        is_valid = False
    
    # Note: RPM limit is automatically controlled by RateLimiter at runtime,
    # so we don't need to validate it here. Concurrency and RPM are different concepts:
    # - Concurrency: number of simultaneous requests
    # - RPM: number of requests per minute
    # The RateLimiter will ensure RPM limits are respected during actual execution.
    
    # Check if page concurrency is too high
    if page_concurrency > 100:
        warnings.append(
            f"页面并发数 ({page_concurrency}) 较高，可能导致API限流。"
            f"建议设置为 50 以下。"
        )
    
    # Check if file count is too high
    if file_count > 10:
        warnings.append(
            f"文件数量 ({file_count}) 较多，建议分批处理以提高稳定性。"
        )
    
    # Check if total requests would exceed daily limit
    # Rough estimate: assume each file has average 50 pages
    estimated_total_requests = file_count * 50
    if estimated_total_requests > rpd_limit * 0.8:  # 80% of daily limit
        warnings.append(
            f"预计总请求数 ({estimated_total_requests}) 接近每日限制 ({rpd_limit})。"
            f"建议分批处理或提高RPD限制。"
        )
    
    return is_valid, warnings


def calculate_safe_concurrency(
    desired_page_concurrency: int,
    file_count: int,
    rpm_limit: int,
    max_global_concurrency: int = 200
) -> Tuple[int, int]:
    """
    Calculate safe concurrency settings based on limits.
    
    Args:
        desired_page_concurrency: Desired page-level concurrency
        file_count: Number of files
        rpm_limit: API RPM limit
        max_global_concurrency: Maximum global concurrency
        
    Returns:
        Tuple of (safe_page_concurrency, safe_file_concurrency)
    """
    from .concurrency_controller import calculate_optimal_concurrency
    
    return calculate_optimal_concurrency(
        desired_page_concurrency,
        file_count,
        rpm_limit,
        max_global_concurrency
    )


def get_concurrency_recommendations(
    file_count: int,
    avg_pages_per_file: int,
    rpm_limit: int
) -> Dict[str, Any]:
    """
    Get concurrency recommendations based on workload.
    
    Args:
        file_count: Number of files
        avg_pages_per_file: Average pages per file
        rpm_limit: API RPM limit
        
    Returns:
        Dictionary with recommendations
    """
    total_pages = file_count * avg_pages_per_file
    
    # Small workload
    if total_pages < 100:
        recommended_page_concurrency = min(50, total_pages)
        recommended_file_concurrency = min(5, file_count)
    # Medium workload
    elif total_pages < 500:
        recommended_page_concurrency = 30
        recommended_file_concurrency = min(3, file_count)
    # Large workload
    else:
        recommended_page_concurrency = 20
        recommended_file_concurrency = min(2, file_count)
    
    # Note: RPM limit is automatically controlled by RateLimiter at runtime,
    # so we don't need to adjust recommendations based on RPM here.
    # The RateLimiter will ensure RPM limits are respected during actual execution.
    
    return {
        "page_concurrency": recommended_page_concurrency,
        "file_concurrency": recommended_file_concurrency,
        "reasoning": f"基于 {total_pages} 总页数和 {rpm_limit} RPM限制的推荐配置"
    }

