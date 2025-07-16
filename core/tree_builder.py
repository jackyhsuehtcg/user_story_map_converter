#!/usr/bin/env python3
"""
Tree Builder for User Story Map Converter

Simple tree structure builder that converts Lark table records into 
hierarchical tree format for mindmap generation.

Core functionality:
- Parse Lark records into tree nodes
- Build parent-child relationships  
- Output structured tree data for mindmap generator

Usage:
    from core.tree_builder import TreeBuilder
    
    builder = TreeBuilder()
    tree_data = builder.build_tree(lark_records)
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TreeNode:
    """Simple tree node representation"""
    record_id: str
    story_no: str
    description: str  # 改為 description，由 "As a" 和 "I want" 組合
    as_a: Optional[str] = None
    i_want: Optional[str] = None
    criteria: Optional[str] = None
    tcg: Optional[str] = None
    parent_id: Optional[str] = None
    children: List['TreeNode'] = field(default_factory=list)
    level: int = 0
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    def add_child(self, child: 'TreeNode'):
        """Add a child node"""
        if child not in self.children:
            self.children.append(child)
            child.parent_id = self.record_id
            child.level = self.level + 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'record_id': self.record_id,
            'story_no': self.story_no,
            'description': self.description,
            'as_a': self.as_a,
            'i_want': self.i_want,
            'criteria': self.criteria,
            'tcg': self.tcg,
            'parent_id': self.parent_id,
            'level': self.level,
            'children': [child.to_dict() for child in self.children]
        }
        # Include extra fields
        if self.extra_fields:
            result['extra_fields'] = self.extra_fields
        return result


class TreeBuilder:
    """Simple tree builder for Lark records"""
    
    def __init__(self, logger: Optional[logging.Logger] = None, config: Optional[Dict[str, Any]] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Configurable field mappings
        self.parent_field_names = self.config.get('parent_field_names', ['Parent Tickets', '父記錄', 'parent'])
        
        # Default field mappings
        default_mappings = {
            'story_no': 'Story.No',
            'as_a': 'As a',
            'i_want': 'I want',
            'features': 'Features',
            'criteria': 'Criteria',
            'tcg': 'TCG'
        }
        
        # Merge with config, ensuring defaults are preserved
        config_mappings = self.config.get('field_mappings', {})
        self.field_mappings = {**default_mappings, **config_mappings}
        self.preserve_extra_fields = self.config.get('preserve_extra_fields', True)
        
        # Story number validation pattern: Story-XXX-YYYYY
        self.story_pattern = re.compile(r'^Story-[A-Z]+(-[A-Z0-9]+)+$', re.IGNORECASE)
        
        # Statistics for filtered records
        self.filtered_stats = {
            'empty_story_no': 0,
            'invalid_format': 0,
            'valid_records': 0
        }
    
    def build_tree(self, lark_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build tree structure from Lark records
        
        Args:
            lark_records: List of Lark table records
            
        Returns:
            Tree structure with root nodes and metadata
        """
        if not lark_records:
            return {'trees': [], 'metadata': self._get_metadata()}
        
        # Reset statistics
        self.filtered_stats = {
            'empty_story_no': 0,
            'invalid_format': 0,
            'valid_records': 0
        }
        
        # Parse records into nodes with validation
        nodes = {}
        for record in lark_records:
            node = self._parse_record(record)
            if node:
                nodes[node.record_id] = node
        
        # Build relationships
        root_nodes = []
        for node in nodes.values():
            if node.parent_id and node.parent_id in nodes:
                parent = nodes[node.parent_id]
                parent.add_child(node)
            else:
                node.parent_id = None
                root_nodes.append(node)
        
        # Set levels
        for root in root_nodes:
            self._set_levels(root, 0)
        
        # Log filtering statistics
        total_records = len(lark_records)
        self.logger.info(f"Record filtering completed: {self.filtered_stats['valid_records']}/{total_records} records passed validation")
        if self.filtered_stats['empty_story_no'] > 0:
            self.logger.info(f"Filtered {self.filtered_stats['empty_story_no']} records with empty Story numbers")
        if self.filtered_stats['invalid_format'] > 0:
            self.logger.info(f"Filtered {self.filtered_stats['invalid_format']} records with invalid Story number format")
        
        return {
            'trees': [root.to_dict() for root in root_nodes],
            'metadata': self._get_metadata()
        }
    
    def _parse_record(self, record: Dict[str, Any]) -> Optional[TreeNode]:
        """Parse single record into TreeNode with Story number validation"""
        record_id = record.get('record_id')
        if not record_id:
            return None
        
        fields = record.get('fields', {})
        
        # Get story number from fields
        story_no = fields.get(self.field_mappings['story_no'], '').strip()
        
        # Validate story number
        if not story_no:
            self.filtered_stats['empty_story_no'] += 1
            self.logger.warning(f"Record {record_id}: Story number is empty, filtering out")
            return None
        
        if not self._is_valid_story_format(story_no):
            self.filtered_stats['invalid_format'] += 1
            self.logger.warning(f"Record {record_id}: Story number '{story_no}' does not match Story-XXX-YYYYY format, filtering out")
            return None
        
        # Record is valid
        self.filtered_stats['valid_records'] += 1
        self.logger.debug(f"Record {record_id}: Valid story number '{story_no}'")
        
        # Get other fields
        as_a = fields.get(self.field_mappings['as_a'], '').strip()
        i_want = fields.get(self.field_mappings['i_want'], '').strip()
        features = fields.get(self.field_mappings['features'], '').strip()
        criteria = fields.get(self.field_mappings['criteria'], '')
        tcg = self._extract_tcg_value(fields)
        
        # 組合 description 從 "As a" 和 "I want" 欄位，若無則回退到 Features
        description = self._build_description(as_a, i_want, features)
        
        parent_id = self._extract_parent_id(fields)
        
        # Collect extra fields if enabled
        extra_fields = {}
        if self.preserve_extra_fields:
            core_fields = set(self.field_mappings.values()) | set(self.parent_field_names)
            for field_name, field_value in fields.items():
                if field_name not in core_fields:
                    extra_fields[field_name] = field_value
        
        return TreeNode(
            record_id=record_id,
            story_no=story_no,
            description=description,
            as_a=as_a if as_a else None,
            i_want=i_want if i_want else None,
            criteria=criteria if criteria else None,
            tcg=tcg,
            parent_id=parent_id,
            extra_fields=extra_fields
        )
    
    def _extract_parent_id(self, fields: Dict[str, Any]) -> Optional[str]:
        """Extract parent ID from fields"""
        for field_name in self.parent_field_names:
            parent_data = fields.get(field_name)
            if not parent_data:
                continue
            
            if isinstance(parent_data, list) and len(parent_data) > 0:
                parent_item = parent_data[0]
                if isinstance(parent_item, dict):
                    record_ids = parent_item.get('record_ids', [])
                    if record_ids:
                        return record_ids[0]
            elif isinstance(parent_data, str):
                return parent_data
        
        return None
    
    def _build_description(self, as_a: str, i_want: str, features: str = '') -> str:
        """
        從 "As a" 和 "I want" 欄位組合生成描述，若無則回退到 Features
        
        Args:
            as_a: "As a" 欄位內容
            i_want: "I want" 欄位內容
            features: "Features" 欄位內容（回退選項）
            
        Returns:
            組合後的描述文字
        """
        # 如果兩個欄位都有內容，組合成完整描述
        if as_a and i_want:
            return f"As a {as_a}, I want {i_want}"
        
        # 如果只有其中一個欄位有內容
        if as_a and not i_want:
            return f"As a {as_a}"
        
        if i_want and not as_a:
            return f"I want {i_want}"
        
        # 如果 As a 和 I want 都沒有內容，回退到 Features
        if features:
            return features
        
        # 如果都沒有內容，返回預設描述
        return "No description"
    
    def _extract_tcg_value(self, fields: Dict[str, Any]) -> Optional[str]:
        """Extract TCG value from fields"""
        tcg_field_name = self.field_mappings.get('tcg', 'TCG')
        tcg_data = fields.get(tcg_field_name)
        
        if not tcg_data:
            return None
        
        # TCG 欄位的格式類似於 Parent Tickets
        if isinstance(tcg_data, list) and len(tcg_data) > 0:
            tcg_item = tcg_data[0]
            if isinstance(tcg_item, dict):
                text_arr = tcg_item.get('text_arr', [])
                if text_arr and len(text_arr) > 0:
                    tcg_value = text_arr[0].strip()
                    if tcg_value:
                        self.logger.debug(f"Found TCG value: {tcg_value}")
                        return tcg_value
        
        return None
    
    def _is_valid_story_format(self, story_no: str) -> bool:
        """
        Validate if story number matches Story-XXX-YYYYY format
        
        Args:
            story_no: Story number to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not story_no or not isinstance(story_no, str):
            return False
        
        # Check against pattern: Story-XXX-YYYYY (e.g., Story-ARD-00001)
        match = self.story_pattern.match(story_no.strip())
        return match is not None
    
    def _set_levels(self, node: TreeNode, level: int):
        """Set node levels recursively"""
        node.level = level
        for child in node.children:
            self._set_levels(child, level + 1)
    
    def _get_metadata(self) -> Dict[str, Any]:
        """Get metadata for the tree"""
        return {
            'build_timestamp': datetime.now().isoformat(),
            'builder_version': '1.0',
            'filtering_stats': self.filtered_stats.copy(),
            'validation_pattern': self.story_pattern.pattern
        }