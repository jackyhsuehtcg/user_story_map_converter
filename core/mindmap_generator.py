#!/usr/bin/env python3
"""
Mindmap Generator for User Story Map Converter

Converts tree structure data into interactive mindmaps using Markmap.
Supports HTML output with custom floating displays for Criteria content.

Core functionality:
- Generate Markmap-compatible Markdown from tree data
- Create interactive HTML mindmaps with JIRA integration  
- Support floating displays for Criteria on hover
- Configurable styling and formatting options

Usage:
    from core.mindmap_generator import MindmapGenerator
    
    generator = MindmapGenerator(config, logger)
    result = generator.generate_mindmap(tree_data, output_path)
"""

import json
import logging
import os
import subprocess
import tempfile
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class MindmapConfig:
    """Mindmap generation configuration"""
    # Markmap settings
    color_freeze_level: int = 2
    max_width: int = 400
    spacing_horizontal: int = 150
    spacing_vertical: int = 15
    auto_fit: bool = True
    font_size: int = 14
    
    # Output settings
    output_formats: List[str] = None
    temp_dir: str = "temp"
    
    # JIRA integration
    jira_enabled: bool = True
    
    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ["html"]


@dataclass
class GenerationResult:
    """Mindmap generation result"""
    success: bool
    message: str
    output_files: Dict[str, str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.output_files is None:
            self.output_files = {}
        if self.metadata is None:
            self.metadata = {}


class MindmapGenerator:
    """Interactive mindmap generator using Markmap"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize mindmap generator
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Initialize paths
        self.temp_dir = Path(self.config.get('temp_dir', 'temp'))
        self.temp_dir.mkdir(exist_ok=True)
        
        # Load mindmap configuration
        self.mindmap_config = self._load_mindmap_config()
        
        # Load JIRA configuration
        self.jira_config = self._load_jira_config()
        
        # Generation statistics
        self.stats = {
            'nodes_processed': 0,
            'criteria_nodes': 0,
            'jira_links': 0,
            'generation_time': 0.0
        }
    
    def _load_mindmap_config(self) -> MindmapConfig:
        """Load mindmap configuration"""
        mindmap_settings = self.config.get('mindmap', {})
        return MindmapConfig(
            color_freeze_level=mindmap_settings.get('color_freeze_level', 2),
            max_width=mindmap_settings.get('max_width', 400),
            spacing_horizontal=mindmap_settings.get('spacing_horizontal', 150),
            spacing_vertical=mindmap_settings.get('spacing_vertical', 15),
            auto_fit=mindmap_settings.get('auto_fit', True),
            font_size=mindmap_settings.get('font_size', 14),
            output_formats=mindmap_settings.get('output_formats', ['html']),
            temp_dir=self.config.get('temp_dir', 'temp'),
            jira_enabled=mindmap_settings.get('jira_enabled', True)
        )
    
    def _load_jira_config(self) -> Dict[str, Any]:
        """Load JIRA configuration"""
        jira_config = self.config.get('jira', {})
        return {
            'base_url': jira_config.get('base_url', 'https://jira.tc-gaming.co/jira'),
            'issue_url_template': jira_config.get('issue_url_template', '{base_url}/browse/{tcg_number}'),
            'link_target': jira_config.get('link_target', '_blank'),
            'link_title_template': jira_config.get('link_title_template', 'Open {tcg_number} in JIRA')
        }
    
    def generate_mindmap(self, tree_data: Dict[str, Any], output_base: str) -> GenerationResult:
        """
        Generate mindmap from tree data
        
        Args:
            tree_data: Tree structure data from TreeBuilder
            output_base: Base path for output files (without extension)
            
        Returns:
            GenerationResult with success status and file paths
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"開始生成心智圖: {output_base}")
            
            # Reset statistics
            self._reset_stats()
            
            # Validate input data
            if not self._validate_tree_data(tree_data):
                return GenerationResult(
                    success=False,
                    message="Invalid tree data structure"
                )
            
            # Generate Markdown content
            markdown_content = self._generate_markdown_from_tree(tree_data)
            if not markdown_content:
                return GenerationResult(
                    success=False,
                    message="Failed to generate Markdown content"
                )
            
            # Save debug Markdown
            debug_md_path = self.temp_dir / "debug_markdown.md"
            with open(debug_md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            self.logger.debug(f"Debug Markdown saved: {debug_md_path}")
            
            # Generate output files
            result_files = {}
            
            # Always generate HTML
            html_path = f"{output_base}.html"
            if self._generate_html_mindmap(markdown_content, html_path):
                result_files['html'] = html_path
                self.logger.info(f"HTML mindmap generated: {html_path}")
            else:
                return GenerationResult(
                    success=False,
                    message="Failed to generate HTML mindmap"
                )
            
            # Generate other formats if requested (placeholder for future implementation)
            for format_type in self.mindmap_config.output_formats:
                if format_type == 'html':
                    continue  # Already generated
                elif format_type == 'png':
                    png_path = f"{output_base}.png"
                    if self._generate_png_mindmap(html_path, png_path):
                        result_files['png'] = png_path
                elif format_type == 'pdf':
                    pdf_path = f"{output_base}.pdf"
                    if self._generate_pdf_mindmap(html_path, pdf_path):
                        result_files['pdf'] = pdf_path
            
            # Calculate generation time
            end_time = datetime.now()
            self.stats['generation_time'] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"心智圖生成完成，耗時 {self.stats['generation_time']:.2f}秒")
            
            return GenerationResult(
                success=True,
                message="Mindmap generated successfully",
                output_files=result_files,
                metadata={
                    'generation_time': self.stats['generation_time'],
                    'stats': self.stats.copy(),
                    'config': {
                        'mindmap': self.mindmap_config.__dict__,
                        'jira': self.jira_config
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"心智圖生成失敗: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            
            return GenerationResult(
                success=False,
                message=f"Generation failed: {str(e)}"
            )
    
    def _validate_tree_data(self, tree_data: Dict[str, Any]) -> bool:
        """Validate tree data structure"""
        if not isinstance(tree_data, dict):
            self.logger.error("Tree data must be a dictionary")
            return False
        
        if 'tree_data' not in tree_data:
            self.logger.error("Missing 'tree_data' key in input")
            return False
        
        trees = tree_data['tree_data'].get('trees', [])
        if not isinstance(trees, list):
            self.logger.error("'trees' must be a list")
            return False
        
        if len(trees) == 0:
            self.logger.warning("No trees found in tree data")
        
        return True
    
    def _reset_stats(self):
        """Reset generation statistics"""
        self.stats = {
            'nodes_processed': 0,
            'criteria_nodes': 0,
            'jira_links': 0,
            'generation_time': 0.0
        }
    
    def _generate_markdown_from_tree(self, tree_data: Dict[str, Any]) -> str:
        """Generate Markmap-compatible Markdown from tree data"""
        lines = []
        
        # Add frontmatter with Markmap configuration
        lines.extend([
            "---",
            "title: User Story Map",
            "markmap:",
            f"  colorFreezeLevel: {self.mindmap_config.color_freeze_level}",
            f"  maxWidth: {self.mindmap_config.max_width}",
            f"  spacingHorizontal: {self.mindmap_config.spacing_horizontal}",
            f"  spacingVertical: {self.mindmap_config.spacing_vertical}",
            f"  autoFit: {str(self.mindmap_config.auto_fit).lower()}",
            f"  fontSize: {self.mindmap_config.font_size}",
            "---",
            "",
        ])
        
        # Process trees
        trees = tree_data['tree_data']['trees']
        
        # Generate root node name
        root_name = self._get_root_node_name(trees)
        lines.extend([
            f"# **{root_name}**",
            ""
        ])
        
        # Sort trees for consistent order
        sorted_trees = sorted(trees, key=lambda x: x.get('story_no', ''))
        
        # Add each tree to Markdown
        for tree in sorted_trees:
            self._add_tree_to_markdown(tree, lines, level=2)
        
        return '\n'.join(lines)
    
    def _add_tree_to_markdown(self, node: Dict[str, Any], lines: List[str], level: int):
        """Recursively add tree node to Markdown"""
        # Build title components
        prefix = '#' * level
        story_no = node.get('story_no', 'Unknown')
        features = node.get('features', 'No description')
        criteria = node.get('criteria', '')
        tcg = node.get('tcg')
        
        # Update statistics
        self.stats['nodes_processed'] += 1
        if criteria:
            self.stats['criteria_nodes'] += 1
        if tcg:
            self.stats['jira_links'] += 1
        
        # Generate story number display (with optional JIRA link)
        story_display = self._generate_jira_link(story_no, tcg)
        
        # Build title with Criteria data attribute for floating display
        criteria_attr = f' data-criteria="{self._escape_html_attr(criteria)}"' if criteria else ''
        title = f'{prefix} <span{criteria_attr}>{story_display}<br/><strong>{features}</strong></span>'
        
        lines.append(title)
        lines.append("")  # Empty line
        
        # Process child nodes
        children = node.get('children', [])
        if children:
            sorted_children = sorted(children, key=lambda x: x.get('story_no', ''))
            for child in sorted_children:
                self._add_tree_to_markdown(child, lines, level + 1)
    
    def _generate_jira_link(self, story_no: str, tcg: Optional[str]) -> str:
        """Generate JIRA link or plain text story number"""
        if not tcg or not self.mindmap_config.jira_enabled:
            return f"<small>{story_no}</small>"
        
        # Build JIRA URL
        base_url = self.jira_config['base_url']
        url_template = self.jira_config['issue_url_template']
        link_target = self.jira_config['link_target']
        title_template = self.jira_config['link_title_template']
        
        jira_url = url_template.format(base_url=base_url, tcg_number=tcg)
        link_title = title_template.format(tcg_number=tcg)
        
        return f'<small><a href="{jira_url}" target="{link_target}" title="{link_title}">{story_no}</a></small>'
    
    def _escape_html_attr(self, text: str) -> str:
        """Escape HTML attribute special characters"""
        if not text:
            return ""
        return (text.replace('"', '&quot;')
                   .replace("'", '&#39;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('&', '&amp;'))
    
    def _get_root_node_name(self, trees: List[Dict[str, Any]]) -> str:
        """Extract root node name from trees"""
        if not trees:
            return "使用者故事地圖"
        
        # Extract middle part from first tree's story number
        first_tree = trees[0]
        story_no = first_tree.get('story_no', 'Story-ARD-00001')
        return self._extract_middle_part(story_no)
    
    def _extract_middle_part(self, story_no: str) -> str:
        """Extract middle part from Story-XXX-YYYYY format"""
        try:
            parts = story_no.split('-')
            if len(parts) >= 3:
                return parts[1]  # Return middle part
            else:
                return story_no
        except:
            return story_no
    
    def _generate_html_mindmap(self, markdown_content: str, output_path: str) -> bool:
        """Generate HTML mindmap using markmap-cli"""
        try:
            # Create temporary Markdown file
            md_file = self.temp_dir / "temp_mindmap.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Use markmap-cli to generate HTML
            cmd = [
                'markmap',
                str(md_file),
                '-o', output_path,
                '--no-open'
            ]
            
            self.logger.debug(f"Executing markmap command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Inject custom styles and scripts for Criteria floating display
                self._inject_custom_enhancements(output_path)
                self.logger.debug(f"HTML mindmap generated successfully: {output_path}")
                return True
            else:
                self.logger.error(f"markmap-cli failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("markmap-cli command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error generating HTML mindmap: {e}")
            return False
        finally:
            # Clean up temporary file
            if md_file.exists():
                md_file.unlink()
    
    def _inject_custom_enhancements(self, html_path: str):
        """Inject custom CSS and JavaScript for enhanced functionality"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Custom CSS for Criteria floating display
            custom_css = self._get_custom_css()
            
            # Custom JavaScript for floating display functionality
            custom_js = self._get_custom_javascript()
            
            # Inject CSS before </head>
            html_content = html_content.replace('</head>', custom_css + '\n</head>')
            
            # Inject JavaScript before </body>
            html_content = html_content.replace('</body>', custom_js + '\n</body>')
            
            # Write back to file
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.debug("Custom enhancements injected successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to inject custom enhancements: {e}")
    
    def _get_custom_css(self) -> str:
        """Get custom CSS for floating display"""
        return """
            <style>
            /* Criteria 浮動顯示樣式 */
            .criteria-tooltip {
                position: absolute;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-family: Arial, sans-serif;
                max-width: 300px;
                word-wrap: break-word;
                z-index: 1000;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.2s ease-in-out;
                border: 1px solid #666;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }
            
            .criteria-tooltip.show {
                opacity: 1;
            }
            
            .criteria-tooltip::before {
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: rgba(0, 0, 0, 0.9) transparent transparent transparent;
            }
            
            </style>
            """
    
    def _get_custom_javascript(self) -> str:
        """Get custom JavaScript for floating display functionality"""
        return """
            <script>
            (function() {
                // 等待 markmap 完全載入
                setTimeout(function() {
                    var tooltip = null;
                    
                    // 從 markmap 的 root 數據中提取 criteria 資訊
                    var criteriaMap = {};
                    
                    function extractCriteriaFromMarkmap() {
                        if (window.mm && window.mm.state && window.mm.state.data) {
                            function traverseNode(node) {
                                if (node.payload && node.payload.lines) {
                                    var lineInfo = node.payload.lines;
                                    // 查找包含 data-criteria 的內容
                                    var content = node.content || '';
                                    var match = content.match(/data-criteria="([^"]*?)"/);
                                    if (match) {
                                        var criteria = match[1];
                                        // 解碼 HTML 實體
                                        var tempDiv = document.createElement('div');
                                        tempDiv.innerHTML = criteria;
                                        criteria = tempDiv.textContent || tempDiv.innerText || '';
                                        
                                        if (criteria.trim()) {
                                            criteriaMap[lineInfo] = criteria;
                                        }
                                    }
                                }
                                if (node.children) {
                                    node.children.forEach(traverseNode);
                                }
                            }
                            traverseNode(window.mm.state.data);
                        }
                    }
                    
                    function createTooltip() {
                        if (!tooltip) {
                            tooltip = document.createElement('div');
                            tooltip.className = 'criteria-tooltip';
                            document.body.appendChild(tooltip);
                        }
                        return tooltip;
                    }
                    
                    function showTooltip(event, criteriaText) {
                        if (!criteriaText || criteriaText.trim() === '') return;
                        
                        var tooltip = createTooltip();
                        tooltip.textContent = criteriaText;
                        tooltip.classList.add('show');
                        
                        // 計算位置
                        var rect = event.target.getBoundingClientRect();
                        var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                        var scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                        
                        tooltip.style.left = (rect.left + scrollLeft + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
                        tooltip.style.top = (rect.top + scrollTop - tooltip.offsetHeight - 10) + 'px';
                    }
                    
                    function hideTooltip() {
                        if (tooltip) {
                            tooltip.classList.remove('show');
                        }
                    }
                    
                    // 為所有節點添加事件監聽器
                    function attachTooltipListeners() {
                        extractCriteriaFromMarkmap();
                        
                        var nodes = document.querySelectorAll('.markmap-node');
                        nodes.forEach(function(node) {
                            // 嘗試從節點的 data 屬性獲取 lines 資訊
                            var nodeData = node.__data__;
                            if (nodeData && nodeData.payload && nodeData.payload.lines) {
                                var criteria = criteriaMap[nodeData.payload.lines];
                                if (criteria && criteria.trim() !== '') {
                                    node.addEventListener('mouseenter', function(e) {
                                        showTooltip(e, criteria);
                                    });
                                    
                                    node.addEventListener('mouseleave', function(e) {
                                        hideTooltip();
                                    });
                                }
                            }
                        });
                    }
                    
                    // 初始化
                    attachTooltipListeners();
                    
                    // 監聽 markmap 更新事件
                    if (window.mm && window.mm.svg) {
                        window.mm.svg.on('markmap-render', attachTooltipListeners);
                    }
                    
                }, 1500);
            })();
            </script>
            """
    
    # Placeholder methods for future format support
    def _generate_png_mindmap(self, html_path: str, output_path: str) -> bool:
        """Generate PNG mindmap from HTML (placeholder)"""
        self.logger.debug(f"PNG generation not implemented: {output_path}")
        return False
    
    def _generate_pdf_mindmap(self, html_path: str, output_path: str) -> bool:
        """Generate PDF mindmap from HTML (placeholder)"""
        self.logger.debug(f"PDF generation not implemented: {output_path}")
        return False
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics"""
        return self.stats.copy()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats"""
        return ['html']  # Only HTML is currently implemented