"""
Comprehensive tests for Concurrency Validator.

This test suite verifies:
1. Configuration validation logic
2. Warning generation
3. Safe concurrency calculation
4. Recommendations generation
5. Edge cases and boundary conditions
"""

import pytest
from unittest.mock import Mock, patch

from app.services.concurrency_validator import (
    validate_concurrency_config,
    calculate_safe_concurrency,
    get_concurrency_recommendations
)


class TestValidateConcurrencyConfig:
    """Test suite for validate_concurrency_config function."""
    
    def test_valid_configuration(self):
        """Test valid configuration."""
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=10,
            file_count=3,
            rpm_limit=100,
            tpm_budget=1000000,
            rpd_limit=10000,
            max_global_concurrency=200
        )
        
        assert is_valid is True
        assert len(warnings) == 0
    
    def test_global_limit_warning(self):
        """Test warning when exceeding global limit."""
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=50,
            file_count=10,
            rpm_limit=100,
            tpm_budget=1000000,
            rpd_limit=10000,
            max_global_concurrency=100
        )
        
        assert is_valid is False
        assert len(warnings) > 0
        assert any("全局限制" in w for w in warnings)
    
    def test_high_page_concurrency_warning(self):
        """Test warning for high page concurrency."""
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=150,
            file_count=2,
            rpm_limit=100,
            tpm_budget=1000000,
            rpd_limit=10000,
            max_global_concurrency=200
        )
        
        assert len(warnings) > 0
        assert any("页面并发数" in w for w in warnings)
    
    def test_high_file_count_warning(self):
        """Test warning for high file count."""
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=10,
            file_count=15,
            rpm_limit=100,
            tpm_budget=1000000,
            rpd_limit=10000,
            max_global_concurrency=200
        )
        
        assert len(warnings) > 0
        assert any("文件数量" in w for w in warnings)
    
    def test_daily_limit_warning(self):
        """Test warning when approaching daily limit."""
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=10,
            file_count=20,
            rpm_limit=100,
            tpm_budget=1000000,
            rpd_limit=1000,  # Low daily limit
            max_global_concurrency=200
        )
        
        # Should warn about daily limit (20 files * 50 pages = 1000 requests)
        assert len(warnings) > 0
        assert any("每日限制" in w or "RPD" in w for w in warnings)
    
    def test_multiple_warnings(self):
        """Test multiple warnings generated."""
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=150,
            file_count=15,
            rpm_limit=100,
            tpm_budget=1000000,
            rpd_limit=1000,
            max_global_concurrency=100
        )
        
        # Should have multiple warnings
        assert len(warnings) >= 2
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Zero values
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=0,
            file_count=0,
            rpm_limit=0,
            tpm_budget=0,
            rpd_limit=0,
            max_global_concurrency=0
        )
        # Should handle gracefully
        assert isinstance(is_valid, bool)
        assert isinstance(warnings, list)
        
        # Very large values
        is_valid, warnings = validate_concurrency_config(
            page_concurrency=10000,
            file_count=1000,
            rpm_limit=100000,
            tpm_budget=100000000,
            rpd_limit=1000000,
            max_global_concurrency=200
        )
        # Should generate warnings
        assert len(warnings) > 0


class TestCalculateSafeConcurrency:
    """Test suite for calculate_safe_concurrency function."""
    
    def test_basic_calculation(self):
        """Test basic safe concurrency calculation."""
        page_conc, file_conc = calculate_safe_concurrency(
            desired_page_concurrency=10,
            file_count=5,
            rpm_limit=100,
            max_global_concurrency=200
        )
        
        assert page_conc > 0
        assert file_conc > 0
    
    def test_global_limit_restriction(self):
        """Test when global limit restricts concurrency."""
        page_conc, file_conc = calculate_safe_concurrency(
            desired_page_concurrency=50,
            file_count=10,
            rpm_limit=100,
            max_global_concurrency=100
        )
        
        # Should be limited by global concurrency
        assert page_conc * file_conc <= 100
    
    def test_delegates_to_optimal_calculation(self):
        """Test that it delegates to calculate_optimal_concurrency."""
        with patch('app.services.concurrency_controller.calculate_optimal_concurrency') as mock_calc:
            mock_calc.return_value = (5, 3)
            
            page_conc, file_conc = calculate_safe_concurrency(
                desired_page_concurrency=10,
                file_count=5,
                rpm_limit=100,
                max_global_concurrency=200
            )
            
            assert page_conc == 5
            assert file_conc == 3
            mock_calc.assert_called_once()


class TestGetConcurrencyRecommendations:
    """Test suite for get_concurrency_recommendations function."""
    
    def test_small_workload(self):
        """Test recommendations for small workload."""
        recommendations = get_concurrency_recommendations(
            file_count=2,
            avg_pages_per_file=30,
            rpm_limit=100
        )
        
        assert "page_concurrency" in recommendations
        assert "file_concurrency" in recommendations
        assert "reasoning" in recommendations
        assert recommendations["page_concurrency"] <= 50
        assert recommendations["file_concurrency"] <= 5
    
    def test_medium_workload(self):
        """Test recommendations for medium workload."""
        recommendations = get_concurrency_recommendations(
            file_count=5,
            avg_pages_per_file=80,
            rpm_limit=100
        )
        
        # Total pages: 400 (medium workload)
        assert recommendations["page_concurrency"] == 30
        assert recommendations["file_concurrency"] <= 3
    
    def test_large_workload(self):
        """Test recommendations for large workload."""
        recommendations = get_concurrency_recommendations(
            file_count=10,
            avg_pages_per_file=100,
            rpm_limit=100
        )
        
        # Total pages: 1000 (large workload)
        assert recommendations["page_concurrency"] == 20
        assert recommendations["file_concurrency"] <= 2
    
    def test_reasoning_included(self):
        """Test that reasoning is included in recommendations."""
        recommendations = get_concurrency_recommendations(
            file_count=3,
            avg_pages_per_file=50,
            rpm_limit=100
        )
        
        assert "reasoning" in recommendations
        assert isinstance(recommendations["reasoning"], str)
        assert "总页数" in recommendations["reasoning"]
        assert "RPM限制" in recommendations["reasoning"]
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Zero files
        recommendations = get_concurrency_recommendations(
            file_count=0,
            avg_pages_per_file=50,
            rpm_limit=100
        )
        assert "page_concurrency" in recommendations
        
        # Very large workload
        recommendations = get_concurrency_recommendations(
            file_count=100,
            avg_pages_per_file=1000,
            rpm_limit=100
        )
        assert recommendations["page_concurrency"] == 20
        assert recommendations["file_concurrency"] <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

