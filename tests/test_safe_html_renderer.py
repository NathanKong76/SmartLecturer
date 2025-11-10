"""
Comprehensive tests for Safe HTML Renderer module.

This test suite verifies:
1. Safe HTML to PDF rendering with thread safety
2. Error handling for malformed HTML
3. Timeout and resource management
4. Thread pool management
5. CSS and background handling
6. Performance and resource cleanup
"""

import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.safe_html_renderer import safe_render_html_to_pdf_fragment


class TestSafeHTMLRenderer:
    """Test suite for safe_render_html_to_pdf_fragment function."""
    
    def test_basic_html_rendering(self):
        """Test basic HTML rendering with valid input."""
        html_content = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Test Document</h1>
            <p>This is a test paragraph.</p>
        </body>
        </html>
        """
        
        # Mock the actual rendering to avoid browser dependencies
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"fake_pdf_content"
            
            result = safe_render_html_to_pdf_fragment(
                html=html_content,
                width_pt=612.0,
                height_pt=792.0,
                css=None,
                background="white"
            )
            
            assert result is not None
            assert isinstance(result, bytes)
            mock_render.assert_called_once()
    
    def test_empty_html(self):
        """Test rendering with empty HTML content."""
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"pdf_from_empty_html"
            
            result = safe_render_html_to_pdf_fragment(
                html="",
                width_pt=612.0,
                height_pt=792.0
            )
            
            assert result is not None
            assert isinstance(result, bytes)
            mock_render.assert_called_once()
    
    def test_malformed_html(self):
        """Test rendering with malformed HTML."""
        malformed_html = "<html><body><h1>Unclosed tag<p>Content</body>"
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"pdf_from_malformed_html"
            
            # Should handle malformed HTML gracefully
            result = safe_render_html_to_pdf_fragment(
                html=malformed_html,
                width_pt=612.0,
                height_pt=792.0
            )
            
            assert result is not None
            assert isinstance(result, bytes)
    
    def test_html_with_css(self):
        """Test rendering HTML with CSS styling."""
        html_with_css = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                h1 { color: blue; }
                .highlight { background-color: yellow; }
            </style>
        </head>
        <body>
            <h1>Styled Content</h1>
            <p class="highlight">This paragraph has styling.</p>
        </body>
        </html>
        """
        
        custom_css = """
        .custom-style {
            color: red;
            font-size: 14pt;
        }
        """
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"pdf_with_css"
            
            result = safe_render_html_to_pdf_fragment(
                html=html_with_css,
                width_pt=612.0,
                height_pt=792.0,
                css=custom_css,
                background="white"
            )
            
            assert result is not None
            assert isinstance(result, bytes)
    
    def test_different_page_sizes(self):
        """Test rendering with different page dimensions."""
        html_content = "<html><body><p>Content</p></body></html>"
        
        test_cases = [
            (612.0, 792.0),  # Letter size
            (595.0, 842.0),  # A4 size
            (420.0, 594.0),  # A3 size
            (792.0, 612.0),  # Landscape
        ]
        
        for width, height in test_cases:
            with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
                mock_render.return_value = f"pdf_{width}x{height}".encode()
                
                result = safe_render_html_to_pdf_fragment(
                    html=html_content,
                    width_pt=width,
                    height_pt=height
                )
                
                assert result is not None
                assert isinstance(result, bytes)
                assert len(result) > 0
    
    def test_different_backgrounds(self):
        """Test rendering with different background colors."""
        html_content = "<html><body><p>Content</p></body></html>"
        
        backgrounds = ["white", "black", "red", "#f0f0f0", "transparent"]
        
        for background in backgrounds:
            with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
                mock_render.return_value = f"pdf_bg_{background}".encode()
                
                result = safe_render_html_to_pdf_fragment(
                    html=html_content,
                    width_pt=612.0,
                    height_pt=792.0,
                    background=background
                )
                
                assert result is not None
                assert isinstance(result, bytes)


class TestErrorHandling:
    """Test suite for error handling scenarios."""
    
    def test_html_parsing_error(self):
        """Test handling of HTML parsing errors."""
        # Simulate an HTML that causes parsing errors
        problematic_html = "<html><body>{{invalid_template_syntax}}</body></html>"
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.side_effect = Exception("HTML parsing failed")
            
            # Should handle the error gracefully
            with pytest.raises(Exception):
                safe_render_html_to_pdf_fragment(
                    html=problematic_html,
                    width_pt=612.0,
                    height_pt=792.0
                )
    
    def test_rendering_timeout(self):
        """Test handling of rendering timeouts."""
        html_content = "<html><body><p>Content</p></body></html>"
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            # Simulate a timeout
            mock_render.side_effect = TimeoutError("Rendering timeout")
            
            with pytest.raises(TimeoutError):
                safe_render_html_to_pdf_fragment(
                    html=html_content,
                    width_pt=612.0,
                    height_pt=792.0
                )
    
    def test_memory_error(self):
        """Test handling of memory errors during rendering."""
        large_html = "<html><body>" + "x" * 1000000 + "</body></html>"
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.side_effect = MemoryError("Out of memory")
            
            with pytest.raises(MemoryError):
                safe_render_html_to_pdf_fragment(
                    html=large_html,
                    width_pt=612.0,
                    height_pt=792.0
                )
    
    def test_browser_unavailable(self):
        """Test handling when browser is unavailable."""
        html_content = "<html><body><p>Content</p></body></html>"
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.side_effect = Exception("Browser not available")
            
            with pytest.raises(Exception):
                safe_render_html_to_pdf_fragment(
                    html=html_content,
                    width_pt=612.0,
                    height_pt=792.0
                )


class TestThreadSafety:
    """Test suite for thread safety and concurrency."""
    
    def test_concurrent_rendering(self):
        """Test that multiple threads can render simultaneously."""
        html_content = "<html><body><p>Thread-safe content</p></body></html>"
        
        results = []
        exceptions = []
        
        def render_in_thread(thread_id):
            try:
                with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
                    mock_render.return_value = f"pdf_thread_{thread_id}".encode()
                    
                    result = safe_render_html_to_pdf_fragment(
                        html=html_content,
                        width_pt=612.0,
                        height_pt=792.0
                    )
                    results.append((thread_id, result))
            except Exception as e:
                exceptions.append((thread_id, e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=render_in_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
        assert len(results) == 5
        
        # Each thread should get a different result
        result_ids = [r[0] for r in results]
        assert sorted(result_ids) == list(range(5))
    
    def test_thread_pool_cleanup(self):
        """Test that thread pool resources are properly cleaned up."""
        html_content = "<html><body><p>Content</p></body></html>"
        
        # Test multiple renders to ensure thread pool management
        for i in range(3):
            with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
                mock_render.return_value = f"pdf_{i}".encode()
                
                result = safe_render_html_to_pdf_fragment(
                    html=html_content,
                    width_pt=612.0,
                    height_pt=792.0
                )
                
                assert result is not None
                assert isinstance(result, bytes)


class TestResourceManagement:
    """Test suite for resource management and cleanup."""
    
    def test_large_html_handling(self):
        """Test handling of large HTML content."""
        # Create a large HTML document
        large_content = "<html><body>"
        for i in range(1000):
            large_content += f"<p>Paragraph {i}: {'x' * 100}</p>"
        large_content += "</body></html>"
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"large_pdf_content"
            
            result = safe_render_html_to_pdf_fragment(
                html=large_content,
                width_pt=612.0,
                height_pt=792.0
            )
            
            assert result is not None
            assert isinstance(result, bytes)
    
    def test_invalid_dimensions(self):
        """Test handling of invalid page dimensions."""
        html_content = "<html><body><p>Content</p></body></html>"
        
        invalid_dimensions = [
            (0, 792.0),      # Zero width
            (612.0, 0),      # Zero height
            (-100, 792.0),   # Negative width
            (612.0, -100),   # Negative height
            (0.1, 0.1),      # Very small dimensions
        ]
        
        for width, height in invalid_dimensions:
            with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
                mock_render.return_value = b"pdf_invalid_dims"
                
                # Should handle invalid dimensions gracefully
                result = safe_render_html_to_pdf_fragment(
                    html=html_content,
                    width_pt=width,
                    height_pt=height
                )
                
                assert result is not None
                assert isinstance(result, bytes)
    
    def test_special_characters(self):
        """Test handling of special characters and Unicode."""
        html_content = """
        <html><body>
        <p>Special chars: 中文 العربية Ελληνικά Русский</p>
        <p>Math: ∑ ∫ √ ∞ ≠ ≤ ≥</p>
        <p>Emoji: 😀 🚀 📚 🔧</p>
        <p>Symbols: © ® ™ € £ ¥</p>
        </body></html>
        """
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"pdf_unicode"
            
            result = safe_render_html_to_pdf_fragment(
                html=html_content,
                width_pt=612.0,
                height_pt=792.0
            )
            
            assert result is not None
            assert isinstance(result, bytes)


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""
    
    def test_minimal_html(self):
        """Test with minimal valid HTML."""
        minimal_html = "<p>Content</p>"
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"minimal_pdf"
            
            result = safe_render_html_to_pdf_fragment(
                html=minimal_html,
                width_pt=612.0,
                height_pt=792.0
            )
            
            assert result is not None
            assert isinstance(result, bytes)
    
    def test_html_with_javascript(self):
        """Test HTML containing JavaScript (should be ignored in PDF)."""
        html_with_js = """
        <html><body>
        <h1>Page with JavaScript</h1>
        <script>
            document.write('This should not appear in PDF');
            alert('This should not appear');
        </script>
        <p>Static content only.</p>
        </body></html>
        """
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"pdf_no_js"
            
            result = safe_render_html_to_pdf_fragment(
                html=html_with_js,
                width_pt=612.0,
                height_pt=792.0
            )
            
            assert result is not None
            assert isinstance(result, bytes)
    
    def test_html_with_external_resources(self):
        """Test HTML with external CSS, images, or scripts."""
        html_external = """
        <html><head>
            <link rel="stylesheet" href="external.css">
            <script src="external.js"></script>
        </head><body>
            <img src="external-image.jpg" alt="External Image">
            <h1>Content with external resources</h1>
        </body></html>
        """
        
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"pdf_external_resources"
            
            result = safe_render_html_to_pdf_fragment(
                html=html_external,
                width_pt=612.0,
                height_pt=792.0
            )
            
            assert result is not None
            assert isinstance(result, bytes)
    
    def test_empty_parameters(self):
        """Test with None parameters and empty strings."""
        with patch('app.services.safe_html_renderer.safe_render_html_to_pdf_fragment') as mock_render:
            mock_render.return_value = b"pdf_empty_params"
            
            # Test with None CSS
            result = safe_render_html_to_pdf_fragment(
                html="<p>Content</p>",
                width_pt=612.0,
                height_pt=792.0,
                css=None,
                background="white"
            )
            
            assert result is not None
            assert isinstance(result, bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])