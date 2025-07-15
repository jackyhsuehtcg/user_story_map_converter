#!/usr/bin/env python3
"""
Tree Analyzer Tool for User Story Map Converter

This tool analyzes Lark table data and builds hierarchical tree structures
from parent-child relationships. It can be used as a standalone tool or
imported as a module.

Features:
- Parse Lark JSON data with parent-child relationships
- Build complete tree structures from flat record data
- Handle multiple root nodes and complex hierarchies
- Export tree structures in various formats
- Comprehensive validation and error detection
- Detailed statistics and analysis

Usage:
    python tools/tree_analyzer.py <lark_json_file> [options]

Example:
    python tools/tree_analyzer.py temp/lark_data_*.json --export temp/tree_output.json --format text
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TreeError(Exception):
    """Base exception for tree analysis errors"""
    pass


class CircularReferenceError(TreeError):
    """Raised when circular references are detected"""
    pass


class InvalidDataError(TreeError):
    """Raised when input data is invalid"""
    pass


@dataclass
class TreeNode:
    """Represents a node in the tree structure"""
    record_id: str
    story_no: str
    features: str
    criteria: Optional[str] = None
    parent_id: Optional[str] = None
    children: List['TreeNode'] = field(default_factory=list)
    level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.children is None:
            self.children = []
        if self.criteria == "":
            self.criteria = None
    
    def add_child(self, child: 'TreeNode'):
        """Add a child node and update relationships"""
        if child not in self.children:
            self.children.append(child)
            child.parent_id = self.record_id
            child.level = self.level + 1
    
    def get_descendants_count(self) -> int:
        """Get total number of descendants"""
        count = len(self.children)
        for child in self.children:
            count += child.get_descendants_count()
        return count
    
    def get_path_to_root(self) -> List[str]:
        """Get the path from this node to root as list of story numbers"""
        path = [self.story_no]
        current = self
        # Note: In a proper implementation, we'd need parent references
        # For now, we'll just return the current node
        return path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        return {
            'record_id': self.record_id,
            'story_no': self.story_no,
            'features': self.features,
            'criteria': self.criteria,
            'parent_id': self.parent_id,
            'level': self.level,
            'children_count': len(self.children),
            'descendants_count': self.get_descendants_count(),
            'children': [child.to_dict() for child in self.children],
            'metadata': self.metadata
        }
    
    def __str__(self):
        return f"{self.story_no}: {self.features}"
    
    def __eq__(self, other):
        return isinstance(other, TreeNode) and self.record_id == other.record_id
    
    def __hash__(self):
        return hash(self.record_id)


class TreeAnalyzer:
    """Analyzes and builds tree structures from Lark table data"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_default_logger()
        
        # Internal state
        self._nodes: Dict[str, TreeNode] = {}
        self._root_nodes: List[TreeNode] = []
        self._parent_child_map: Dict[str, List[str]] = {}
        
        # Configuration
        self.parent_field_names = ['Parent Tickets', '父記錄', 'parent', 'parent_record']
        self.max_depth = 20  # Maximum allowed tree depth
        
        # Statistics
        self._stats = {
            'total_nodes': 0,
            'root_nodes': 0,
            'leaf_nodes': 0,
            'max_depth': 0,
            'orphan_nodes': 0,
            'circular_refs': 0,
            'processing_time': 0.0
        }
    
    def _setup_default_logger(self) -> logging.Logger:
        """Setup default logger for the analyzer"""
        logger = logging.getLogger('tree_analyzer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def load_lark_data(self, json_file_path: str) -> Dict[str, Any]:
        """
        Load Lark data from JSON file
        
        Args:
            json_file_path: Path to JSON file containing Lark table data
            
        Returns:
            Loaded JSON data
            
        Raises:
            FileNotFoundError: If JSON file doesn't exist
            InvalidDataError: If JSON is invalid or missing required fields
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate data structure
            if 'table_records' not in data:
                raise InvalidDataError("JSON 檔案缺少 'table_records' 欄位")
            
            self.logger.info(f"成功載入 JSON 資料: {json_file_path}")
            self.logger.debug(f"資料包含 {len(data['table_records'])} 筆記錄")
            
            return data
            
        except FileNotFoundError:
            self.logger.error(f"JSON 檔案不存在: {json_file_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 格式錯誤: {e}")
            raise InvalidDataError(f"JSON 格式錯誤: {e}")
        except Exception as e:
            self.logger.error(f"載入檔案失敗: {e}")
            raise InvalidDataError(f"載入檔案失敗: {e}")
    
    def analyze_tree_structure(self, lark_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze tree structure from Lark data
        
        Args:
            lark_data: Lark table data dictionary
            
        Returns:
            Analysis results including tree structure and statistics
            
        Raises:
            TreeError: If analysis fails
        """
        start_time = datetime.now()
        
        try:
            self.logger.info("開始分析樹狀結構")
            
            # Reset internal state
            self._nodes.clear()
            self._root_nodes.clear()
            self._parent_child_map.clear()
            
            # Parse records into nodes
            records = lark_data.get('table_records', [])
            if not records:
                raise InvalidDataError("沒有找到表格記錄")
            
            self._parse_records(records)
            self._build_tree_relationships()
            self._validate_tree_structure()
            self._calculate_statistics()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self._stats['processing_time'] = processing_time
            
            self.logger.info(f"樹狀結構分析完成，耗時 {processing_time:.3f} 秒")
            
            return self._generate_analysis_result()
            
        except Exception as e:
            self.logger.error(f"樹狀結構分析失敗: {e}")
            raise TreeError(f"樹狀結構分析失敗: {e}")
    
    def _parse_records(self, records: List[Dict[str, Any]]):
        """Parse records into TreeNode objects"""
        self.logger.debug(f"開始解析 {len(records)} 筆記錄")
        
        for i, record in enumerate(records, 1):
            try:
                node = self._parse_single_record(record)
                if node:
                    self._nodes[node.record_id] = node
                    self.logger.debug(f"解析記錄 {i}/{len(records)}: {node.story_no}")
                else:
                    self.logger.warning(f"跳過無效記錄 {i}")
                    
            except Exception as e:
                self.logger.error(f"解析記錄 {i} 失敗: {e}")
                continue
        
        self.logger.info(f"成功解析 {len(self._nodes)} 個節點")
    
    def _parse_single_record(self, record: Dict[str, Any]) -> Optional[TreeNode]:
        """Parse a single record into TreeNode"""
        record_id = record.get('record_id')
        if not record_id:
            self.logger.warning("記錄缺少 record_id")
            return None
        
        fields = record.get('fields', {})
        
        # Extract basic information
        story_no = fields.get('Story.No', f'Unknown-{record_id[:8]}')
        features = fields.get('Features', 'No description')
        criteria = fields.get('Criteria', '')
        
        # Create node with metadata
        node = TreeNode(
            record_id=record_id,
            story_no=story_no,
            features=features,
            criteria=criteria if criteria else None,
            metadata={
                'original_record': record,
                'field_count': len(fields)
            }
        )
        
        # Parse parent relationships
        parent_id = self._extract_parent_id(fields)
        if parent_id:
            node.parent_id = parent_id
            
            # Update parent-child mapping
            if parent_id not in self._parent_child_map:
                self._parent_child_map[parent_id] = []
            self._parent_child_map[parent_id].append(record_id)
        
        return node
    
    def _extract_parent_id(self, fields: Dict[str, Any]) -> Optional[str]:
        """Extract parent record ID from fields"""
        for parent_field_name in self.parent_field_names:
            parent_data = fields.get(parent_field_name)
            if not parent_data:
                continue
            
            # Handle list format (Lark API response format)
            if isinstance(parent_data, list) and len(parent_data) > 0:
                parent_item = parent_data[0]
                
                if isinstance(parent_item, dict):
                    # Check for record_ids field
                    record_ids = parent_item.get('record_ids', [])
                    if record_ids and len(record_ids) > 0:
                        return record_ids[0]
            
            # Handle direct string format
            elif isinstance(parent_data, str):
                return parent_data
        
        return None
    
    def _build_tree_relationships(self):
        """Build parent-child relationships in the tree"""
        self.logger.debug("建立父子關係")
        
        # Identify root nodes
        for node in self._nodes.values():
            if not node.parent_id:
                self._root_nodes.append(node)
        
        # Build parent-child relationships
        for node in self._nodes.values():
            if node.parent_id and node.parent_id in self._nodes:
                parent_node = self._nodes[node.parent_id]
                parent_node.add_child(node)
        
        # Calculate levels
        self._calculate_node_levels()
        
        self.logger.info(f"建立樹狀結構：{len(self._root_nodes)} 個根節點")
    
    def _calculate_node_levels(self):
        """Calculate depth levels for all nodes"""
        for root in self._root_nodes:
            self._set_node_levels(root, 0)
    
    def _set_node_levels(self, node: TreeNode, level: int):
        """Recursively set node levels"""
        node.level = level
        for child in node.children:
            self._set_node_levels(child, level + 1)
    
    def _validate_tree_structure(self):
        """Validate the tree structure for errors"""
        self.logger.debug("驗證樹狀結構")
        
        # Check for circular references
        self._check_circular_references()
        
        # Check for orphan nodes
        orphan_count = 0
        for node in self._nodes.values():
            if node.parent_id and node.parent_id not in self._nodes:
                orphan_count += 1
                self.logger.warning(f"孤兒節點: {node.story_no} (父節點 {node.parent_id} 不存在)")
        
        self._stats['orphan_nodes'] = orphan_count
        
        if orphan_count > 0:
            self.logger.warning(f"發現 {orphan_count} 個孤兒節點")
        
        self.logger.debug("樹狀結構驗證完成")
    
    def _check_circular_references(self):
        """Check for circular references in the tree"""
        visited = set()
        rec_stack = set()
        circular_count = 0
        
        for root in self._root_nodes:
            if self._has_cycle_dfs(root, visited, rec_stack):
                circular_count += 1
        
        self._stats['circular_refs'] = circular_count
        
        if circular_count > 0:
            raise CircularReferenceError(f"檢測到 {circular_count} 個循環參照")
    
    def _has_cycle_dfs(self, node: TreeNode, visited: Set[str], rec_stack: Set[str]) -> bool:
        """Check for cycles using DFS"""
        visited.add(node.record_id)
        rec_stack.add(node.record_id)
        
        for child in node.children:
            if child.record_id not in visited:
                if self._has_cycle_dfs(child, visited, rec_stack):
                    return True
            elif child.record_id in rec_stack:
                self.logger.error(f"檢測到循環參照: {node.record_id} -> {child.record_id}")
                return True
        
        rec_stack.remove(node.record_id)
        return False
    
    def _calculate_statistics(self):
        """Calculate comprehensive statistics"""
        total_nodes = len(self._nodes)
        root_count = len(self._root_nodes)
        leaf_count = sum(1 for node in self._nodes.values() if not node.children)
        
        # Calculate maximum depth
        max_depth = 0
        for root in self._root_nodes:
            depth = self._get_max_depth(root)
            max_depth = max(max_depth, depth)
        
        self._stats.update({
            'total_nodes': total_nodes,
            'root_nodes': root_count,
            'leaf_nodes': leaf_count,
            'max_depth': max_depth
        })
    
    def _get_max_depth(self, node: TreeNode) -> int:
        """Get maximum depth from a node"""
        if not node.children:
            return node.level
        
        return max(self._get_max_depth(child) for child in node.children)
    
    def _generate_analysis_result(self) -> Dict[str, Any]:
        """Generate comprehensive analysis result"""
        # Level distribution
        level_counts = {}
        for node in self._nodes.values():
            level = node.level
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # Node details
        root_details = []
        for root in self._root_nodes:
            root_details.append({
                'story_no': root.story_no,
                'features': root.features,
                'descendants': root.get_descendants_count()
            })
        
        return {
            'trees': [root.to_dict() for root in self._root_nodes],
            'statistics': {
                **self._stats,
                'level_distribution': level_counts,
                'root_details': root_details
            },
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'analyzer_version': '1.0',
                'source_format': 'lark_json'
            }
        }
    
    def export_analysis(self, result: Dict[str, Any], output_file: str, format_type: str = 'json'):
        """
        Export analysis result to file
        
        Args:
            result: Analysis result dictionary
            output_file: Output file path
            format_type: Output format ('json', 'text', 'markdown')
        """
        try:
            if format_type.lower() == 'json':
                self._export_json(result, output_file)
            elif format_type.lower() == 'text':
                self._export_text(result, output_file)
            elif format_type.lower() == 'markdown':
                self._export_markdown(result, output_file)
            else:
                raise ValueError(f"不支援的格式: {format_type}")
            
            self.logger.info(f"分析結果已匯出到: {output_file} (格式: {format_type})")
            
        except Exception as e:
            self.logger.error(f"匯出失敗: {e}")
            raise
    
    def _export_json(self, result: Dict[str, Any], output_file: str):
        """Export result as JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    def _export_text(self, result: Dict[str, Any], output_file: str):
        """Export result as readable text"""
        lines = []
        lines.append("=" * 80)
        lines.append("🌳 User Story Map Tree Analysis")
        lines.append("=" * 80)
        
        # Statistics
        stats = result['statistics']
        lines.append(f"\n📊 統計資訊:")
        lines.append(f"  總節點數: {stats['total_nodes']}")
        lines.append(f"  根節點數: {stats['root_nodes']}")
        lines.append(f"  葉節點數: {stats['leaf_nodes']}")
        lines.append(f"  最大深度: {stats['max_depth']}")
        lines.append(f"  處理時間: {stats['processing_time']:.3f} 秒")
        
        # Level distribution
        level_dist = stats['level_distribution']
        lines.append(f"\n📈 層級分布: {dict(sorted(level_dist.items()))}")
        
        # Tree structures
        lines.append(f"\n🌲 樹狀結構:")
        for i, tree_data in enumerate(result['trees'], 1):
            lines.append(f"\n📍 Tree {i}: {tree_data['story_no']}")
            lines.append("-" * 40)
            self._format_tree_text(tree_data, lines, "")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _format_tree_text(self, node_data: Dict[str, Any], lines: List[str], prefix: str):
        """Format tree structure as text"""
        connector = "└── " if prefix.endswith("    ") else "├── "
        if not prefix:
            connector = ""
        
        features = node_data['features']
        level_info = f" (Level {node_data['level']})" if node_data['level'] > 0 else ""
        lines.append(f"{prefix}{connector}{node_data['story_no']}: {features}{level_info}")
        
        children = node_data.get('children', [])
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = prefix + ("    " if is_last else "│   ")
            self._format_tree_text(child, lines, child_prefix)
    
    def _export_markdown(self, result: Dict[str, Any], output_file: str):
        """Export result as Markdown"""
        lines = []
        lines.append("# User Story Map Tree Analysis")
        lines.append("")
        
        # Metadata
        metadata = result['metadata']
        lines.append(f"**Analysis Time**: {metadata['analysis_timestamp']}")
        lines.append(f"**Analyzer Version**: {metadata['analyzer_version']}")
        lines.append("")
        
        # Statistics
        stats = result['statistics']
        lines.append("## 📊 Statistics")
        lines.append("")
        lines.append(f"- **Total Nodes**: {stats['total_nodes']}")
        lines.append(f"- **Root Nodes**: {stats['root_nodes']}")
        lines.append(f"- **Leaf Nodes**: {stats['leaf_nodes']}")
        lines.append(f"- **Max Depth**: {stats['max_depth']}")
        lines.append(f"- **Processing Time**: {stats['processing_time']:.3f}s")
        lines.append("")
        
        # Tree structures
        lines.append("## 🌲 Tree Structures")
        lines.append("")
        
        for i, tree_data in enumerate(result['trees'], 1):
            lines.append(f"### Tree {i}: {tree_data['story_no']}")
            lines.append("")
            lines.append("```")
            text_lines = []
            self._format_tree_text(tree_data, text_lines, "")
            lines.extend(text_lines)
            lines.append("```")
            lines.append("")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def print_tree_summary(self, result: Dict[str, Any]):
        """Print a summary of the tree analysis"""
        stats = result['statistics']
        
        print("=" * 80)
        print("🌳 User Story Map Tree Analysis Summary")
        print("=" * 80)
        
        print(f"\n📊 統計資訊:")
        print(f"  總節點數: {stats['total_nodes']}")
        print(f"  根節點數: {stats['root_nodes']}")
        print(f"  葉節點數: {stats['leaf_nodes']}")
        print(f"  最大深度: {stats['max_depth']}")
        print(f"  處理時間: {stats['processing_time']:.3f} 秒")
        
        if stats.get('orphan_nodes', 0) > 0:
            print(f"  ⚠️  孤兒節點: {stats['orphan_nodes']}")
        
        level_dist = stats['level_distribution']
        print(f"\n📈 層級分布: {dict(sorted(level_dist.items()))}")
        
        print(f"\n🎯 根節點列表:")
        for i, root_detail in enumerate(stats['root_details'], 1):
            desc_count = root_detail['descendants']
            print(f"  {i}. {root_detail['story_no']}: {root_detail['features']}")
            print(f"     └── {desc_count} 個子節點")


def main():
    """Main function for standalone usage"""
    parser = argparse.ArgumentParser(
        description="Analyze tree structure from Lark table data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python tools/tree_analyzer.py temp/lark_data_*.json
  
  # Export to JSON
  python tools/tree_analyzer.py temp/lark_data_*.json --export temp/tree_analysis.json
  
  # Export as text with verbose output
  python tools/tree_analyzer.py temp/lark_data_*.json --export temp/tree.txt --format text -v
  
  # Export as Markdown
  python tools/tree_analyzer.py temp/lark_data_*.json --export temp/tree.md --format markdown
        """
    )
    
    parser.add_argument(
        'json_file',
        help='Path to JSON file with Lark table data'
    )
    
    parser.add_argument(
        '--export', '-e',
        help='Export analysis result to file'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['json', 'text', 'markdown'],
        default='json',
        help='Export format (default: json)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress detailed output'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(level=level)
    
    try:
        # Create analyzer
        analyzer = TreeAnalyzer()
        
        # Load and analyze data
        lark_data = analyzer.load_lark_data(args.json_file)
        result = analyzer.analyze_tree_structure(lark_data)
        
        # Print summary
        if not args.quiet:
            analyzer.print_tree_summary(result)
        
        # Export if requested
        if args.export:
            analyzer.export_analysis(result, args.export, args.format)
            print(f"\n✅ Analysis exported to: {args.export}")
        
        print(f"\n✅ Tree analysis completed successfully")
        
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()