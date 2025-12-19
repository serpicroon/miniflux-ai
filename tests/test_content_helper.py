"""
Unit tests for core.content_helper module using unittest
"""

import unittest
from unittest.mock import Mock, patch

from core.content_helper import (
    get_content_length,
    to_markdown,
    to_html,
    parse_entry_content,
    build_ordered_content,
    MARKER
)


class TestGetContentLength(unittest.TestCase):
    """Tests for get_content_length function"""
    
    def test_simple_chinese_text(self):
        """Test token counting for simple Chinese text"""
        entry = {'content': "<p>这是一篇测试文章</p>"}
        length = get_content_length(entry)
        # Should be around 8-10 tokens for 8 Chinese characters
        self.assertGreaterEqual(length, 6)
        self.assertLessEqual(length, 12)
    
    def test_simple_english_text(self):
        """Test token counting for simple English text"""
        entry = {'content': "<p>This is a test article</p>"}
        length = get_content_length(entry)
        # Should be around 6-8 tokens for 5 words
        self.assertGreaterEqual(length, 4)
        self.assertLessEqual(length, 10)
    
    def test_mixed_chinese_english(self):
        """Test token counting for mixed Chinese and English"""
        entry = {'content': "<p>这是 a test 文章</p>"}
        length = get_content_length(entry)
        self.assertGreater(length, 0)
    
    def test_empty_html(self):
        """Test empty HTML returns 0 tokens"""
        entry = {'content': ""}
        length = get_content_length(entry)
        self.assertEqual(length, 0)
    
    def test_html_with_only_whitespace(self):
        """Test HTML with only whitespace returns 0 tokens"""
        entry = {'content': "<p>   \n\t   </p>"}
        length = get_content_length(entry)
        self.assertEqual(length, 0)
    
    def test_removes_script_tags(self):
        """Test that script tags are removed before counting"""
        entry = {'content': """
        <script>console.log('This should be ignored');</script>
        <p>Valid content</p>
        """}
        length = get_content_length(entry)
        # Should only count "Valid content", not the script
        self.assertGreaterEqual(length, 1)
        self.assertLessEqual(length, 4)
    
    def test_removes_style_tags(self):
        """Test that style tags are removed before counting"""
        entry = {'content': """
        <style>body { color: red; }</style>
        <p>Valid content</p>
        """}
        length = get_content_length(entry)
        self.assertGreaterEqual(length, 1)
        self.assertLessEqual(length, 4)
    
    def test_removes_noscript_tags(self):
        """Test that noscript tags are removed before counting"""
        entry = {'content': """
        <noscript>Please enable JavaScript</noscript>
        <p>Valid content</p>
        """}
        length = get_content_length(entry)
        self.assertGreaterEqual(length, 1)
        self.assertLessEqual(length, 4)
    
    def test_removes_iframe_tags(self):
        """Test that iframe tags are removed before counting"""
        entry = {'content': """
        <iframe src="https://example.com"></iframe>
        <p>Valid content</p>
        """}
        length = get_content_length(entry)
        self.assertGreaterEqual(length, 1)
        self.assertLessEqual(length, 4)
    
    def test_multiple_paragraphs(self):
        """Test counting tokens across multiple paragraphs"""
        entry = {'content': """
        <p>First paragraph</p>
        <p>Second paragraph</p>
        <p>Third paragraph</p>
        """}
        length = get_content_length(entry)
        self.assertGreater(length, 0)
    
    def test_nested_html_tags(self):
        """Test counting with nested HTML tags"""
        entry = {'content': "<div><p>Nested <strong>content</strong> here</p></div>"}
        length = get_content_length(entry)
        self.assertGreaterEqual(length, 2)
        self.assertLessEqual(length, 6)
    
    def test_html_entities(self):
        """Test that HTML entities are decoded"""
        entry = {'content': "<p>&lt;Hello&gt; &amp; &quot;World&quot;</p>"}
        length = get_content_length(entry)
        self.assertGreater(length, 0)
    
    def test_image_gallery(self):
        """Test filtering out image gallery content"""
        entry = {'content': """
        <img src="1.jpg">
        <img src="2.jpg">
        <img src="3.jpg">
        <p>图集</p>
        """}
        length = get_content_length(entry)
        # Should only count "图集" (2 chars ≈ 2 tokens)
        self.assertGreaterEqual(length, 1)
        self.assertLessEqual(length, 4)
    
    def test_preserves_spaces_between_words(self):
        """Test that spaces are preserved for proper tokenization"""
        entry = {'content': "<p>Word1 Word2 Word3</p>"}
        length = get_content_length(entry)
        # With spaces: proper word boundaries
        self.assertGreaterEqual(length, 2)
        self.assertLessEqual(length, 6)


class TestToMarkdown(unittest.TestCase):
    """Tests for to_markdown function"""
    
    def test_simple_paragraph(self):
        """Test converting simple paragraph"""
        html = "<p>Hello World</p>"
        md = to_markdown(html)
        self.assertIn("Hello World", md)
    
    def test_heading_conversion(self):
        """Test converting headings"""
        html = "<h1>Title</h1>"
        md = to_markdown(html)
        self.assertTrue("#" in md or "Title" in md)
    
    def test_link_conversion(self):
        """Test converting links"""
        html = '<a href="https://example.com">Link</a>'
        md = to_markdown(html)
        self.assertIn("Link", md)
        self.assertIn("[Link](https://example.com)", md)
    
    def test_bold_conversion(self):
        """Test converting bold text"""
        html = "<strong>Bold</strong>"
        md = to_markdown(html)
        self.assertIn("Bold", md)
    
    def test_italic_conversion(self):
        """Test converting italic text"""
        html = "<em>Italic</em>"
        md = to_markdown(html)
        self.assertIn("Italic", md)
    
    def test_list_conversion(self):
        """Test converting lists"""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        md = to_markdown(html)
        self.assertIn("Item 1", md)
        self.assertIn("Item 2", md)
    
    def test_empty_html(self):
        """Test converting empty HTML"""
        html = ""
        md = to_markdown(html)
        self.assertEqual(md, "")
    
    def test_chinese_content(self):
        """Test converting Chinese content"""
        html = "<p>这是中文内容</p>"
        md = to_markdown(html)
        self.assertIn("这是中文内容", md)


class TestToHtml(unittest.TestCase):
    """Tests for to_html function"""
    
    def test_simple_text(self):
        """Test converting plain text"""
        md = "Hello World"
        html = to_html(md)
        self.assertIn("Hello World", html)
    
    def test_heading_conversion(self):
        """Test converting markdown heading"""
        md = "# Title"
        html = to_html(md)
        self.assertIn("Title", html)
        self.assertTrue("<h1>" in html or "h1" in html.lower())
    
    def test_bold_conversion(self):
        """Test converting bold markdown"""
        md = "**Bold Text**"
        html = to_html(md)
        self.assertIn("Bold Text", html)
        self.assertTrue("<strong>" in html or "<b>" in html)
    
    def test_italic_conversion(self):
        """Test converting italic markdown"""
        md = "*Italic Text*"
        html = to_html(md)
        self.assertIn("Italic Text", html)
    
    def test_link_conversion(self):
        """Test converting markdown link"""
        md = "[Link](https://example.com)"
        html = to_html(md)
        self.assertIn("Link", html)
        self.assertIn("example.com", html)
    
    def test_list_conversion(self):
        """Test converting markdown list"""
        md = "- Item 1\n- Item 2"
        html = to_html(md)
        self.assertIn("Item 1", html)
        self.assertIn("Item 2", html)
    
    def test_code_block(self):
        """Test converting code block"""
        md = "```python\nprint('hello')\n```"
        html = to_html(md)
        self.assertIn("print", html)
        self.assertIn("hello", html)
    
    def test_empty_markdown(self):
        """Test converting empty markdown"""
        md = ""
        html = to_html(md)
        self.assertIn(html, ["", "<p></p>", "\n"])
    
    def test_chinese_content(self):
        """Test converting Chinese markdown"""
        md = "这是**中文**内容"
        html = to_html(md)
        self.assertIn("中文", html)


class TestParseEntryContent(unittest.TestCase):
    """Tests for parse_entry_content function"""
    
    def test_no_markers(self):
        """Test parsing content without markers"""
        content = "<p>Original content</p>"
        original, agents = parse_entry_content(content)
        self.assertEqual(original, content)
        self.assertEqual(agents, {})
    
    def test_single_agent_marker(self):
        """Test parsing content with single agent marker"""
        agent_content = "<p>Agent result</p>"
        marker = MARKER.format("summary")
        original = "<p>Original content</p>"
        content = agent_content + marker + original
        
        parsed_original, agents = parse_entry_content(content)
        self.assertEqual(parsed_original, original)
        self.assertIn("summary", agents)
        self.assertEqual(agents["summary"], agent_content)
    
    def test_multiple_agent_markers(self):
        """Test parsing content with multiple agent markers"""
        summary_content = "<p>Summary</p>"
        translate_content = "<p>Translation</p>"
        summary_marker = MARKER.format("summary")
        translate_marker = MARKER.format("translate")
        original = "<p>Original</p>"
        
        content = (summary_content + summary_marker + 
                  translate_content + translate_marker + 
                  original)
        
        parsed_original, agents = parse_entry_content(content)
        self.assertEqual(parsed_original, original)
        self.assertEqual(len(agents), 2)
        self.assertEqual(agents["summary"], summary_content)
        self.assertEqual(agents["translate"], translate_content)
    
    def test_empty_agent_content(self):
        """Test parsing when agent content is empty"""
        marker = MARKER.format("summary")
        original = "<p>Original</p>"
        content = marker + original
        
        parsed_original, agents = parse_entry_content(content)
        self.assertEqual(parsed_original, original)
        self.assertEqual(agents, {})
    
    def test_whitespace_handling(self):
        """Test that whitespace is properly stripped"""
        agent_content = "  <p>Agent result</p>  "
        marker = MARKER.format("summary")
        original = "  <p>Original</p>  "
        content = agent_content + marker + original
        
        parsed_original, agents = parse_entry_content(content)
        self.assertEqual(parsed_original.strip(), original.strip())
        self.assertEqual(agents["summary"].strip(), agent_content.strip())


class TestBuildOrderedContent(unittest.TestCase):
    """Tests for build_ordered_content function"""
    
    @patch('core.content_helper.config')
    def test_no_agent_contents(self, mock_config):
        """Test building content with no agent contents"""
        original = "<p>Original content</p>"
        result = build_ordered_content({}, original)
        self.assertEqual(result, original)
    
    @patch('core.content_helper.config')
    def test_single_agent_content(self, mock_config):
        """Test building content with single agent content"""
        mock_config.agents.keys.return_value = ["summary"]
        
        agent_contents = {"summary": "<p>Summary</p>"}
        original = "<p>Original</p>"
        
        result = build_ordered_content(agent_contents, original)
        
        self.assertIn("<p>Summary</p>", result)
        self.assertIn(MARKER.format("summary"), result)
        self.assertIn("<p>Original</p>", result)
        # Check order: agent content, marker, original
        self.assertLess(result.index("<p>Summary</p>"), result.index(MARKER.format("summary")))
        self.assertLess(result.index(MARKER.format("summary")), result.index("<p>Original</p>"))
    
    @patch('core.content_helper.config')
    def test_multiple_agent_contents(self, mock_config):
        """Test building content with multiple agent contents in order"""
        mock_config.agents.keys.return_value = ["summary", "translate"]
        
        agent_contents = {
            "summary": "<p>Summary</p>",
            "translate": "<p>Translation</p>"
        }
        original = "<p>Original</p>"
        
        result = build_ordered_content(agent_contents, original)
        
        # Check all parts are present
        self.assertIn("<p>Summary</p>", result)
        self.assertIn("<p>Translation</p>", result)
        self.assertIn(MARKER.format("summary"), result)
        self.assertIn(MARKER.format("translate"), result)
        self.assertIn("<p>Original</p>", result)
        
        # Check order follows config.agents order
        summary_idx = result.index("<p>Summary</p>")
        translate_idx = result.index("<p>Translation</p>")
        original_idx = result.index("<p>Original</p>")
        
        self.assertLess(summary_idx, translate_idx)
        self.assertLess(translate_idx, original_idx)
    
    @patch('core.content_helper.config')
    def test_respects_config_order(self, mock_config):
        """Test that agent order follows config, not dict order"""
        # Config defines order as: translate, summary
        mock_config.agents.keys.return_value = ["translate", "summary"]
        
        # Dict provides them in different order
        agent_contents = {
            "summary": "<p>Summary</p>",
            "translate": "<p>Translation</p>"
        }
        original = "<p>Original</p>"
        
        result = build_ordered_content(agent_contents, original)
        
        # Should follow config order: translate before summary
        translate_idx = result.index("<p>Translation</p>")
        summary_idx = result.index("<p>Summary</p>")
        
        self.assertLess(translate_idx, summary_idx)
    
    @patch('core.content_helper.config')
    def test_skips_missing_agents(self, mock_config):
        """Test that missing agents in contents are skipped"""
        mock_config.agents.keys.return_value = ["summary", "translate", "custom"]
        
        agent_contents = {
            "summary": "<p>Summary</p>"
            # translate and custom are missing
        }
        original = "<p>Original</p>"
        
        result = build_ordered_content(agent_contents, original)
        
        self.assertIn("<p>Summary</p>", result)
        self.assertIn(MARKER.format("summary"), result)
        self.assertNotIn(MARKER.format("translate"), result)
        self.assertNotIn(MARKER.format("custom"), result)
        self.assertIn("<p>Original</p>", result)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple functions"""
    
    @patch('core.content_helper.config')
    def test_full_workflow(self, mock_config):
        """Test complete workflow: build, parse, rebuild"""
        mock_config.agents.keys.return_value = ["summary", "translate"]
        
        # Original content
        original = "<p>Original article content</p>"
        
        # Simulate agent processing
        agent_contents = {
            "summary": "<p>This is a summary</p>",
            "translate": "<p>这是翻译</p>"
        }
        
        # Build ordered content
        built_content = build_ordered_content(agent_contents, original)
        
        # Parse it back
        parsed_original, parsed_agent_contents = parse_entry_content(built_content)
        
        # Verify round-trip
        self.assertEqual(parsed_original, original)
        self.assertEqual(len(parsed_agent_contents), 2)
        self.assertEqual(parsed_agent_contents["summary"], agent_contents["summary"])
        self.assertEqual(parsed_agent_contents["translate"], agent_contents["translate"])
    
    def test_html_markdown_roundtrip(self):
        """Test HTML -> Markdown -> HTML conversion"""
        original_html = "<p><strong>Bold</strong> and <em>italic</em> text</p>"
        
        # Convert to markdown
        markdown = to_markdown(original_html)
        
        # Convert back to HTML
        result_html = to_html(markdown)
        
        # Check essential content is preserved
        self.assertIn("Bold", result_html)
        self.assertIn("italic", result_html)
        self.assertIn("text", result_html)


if __name__ == '__main__':
    unittest.main()
