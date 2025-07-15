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
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TreeNode:
    """Simple tree node representation"""
    record_id: str
    story_no: str
    features: str
    criteria: Optional[str] = None
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
            'features': self.features,
            'criteria': self.criteria,
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
        self.field_mappings = self.config.get('field_mappings', {
            'story_no': 'Story.No',
            'features': 'Features', 
            'criteria': 'Criteria'
        })
        self.preserve_extra_fields = self.config.get('preserve_extra_fields', True)
    
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
        
        # Parse records into nodes
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
        
        return {
            'trees': [root.to_dict() for root in root_nodes],
            'metadata': self._get_metadata()
        }
    
    def _parse_record(self, record: Dict[str, Any]) -> Optional[TreeNode]:
        """Parse single record into TreeNode"""
        record_id = record.get('record_id')
        if not record_id:
            return None
        
        fields = record.get('fields', {})
        
        # Use configurable field mappings
        story_no = fields.get(self.field_mappings['story_no'], f'Unknown-{record_id[:8]}')
        features = fields.get(self.field_mappings['features'], 'No description')
        criteria = fields.get(self.field_mappings['criteria'], '')
        
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
            features=features,
            criteria=criteria if criteria else None,
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
    
    def _set_levels(self, node: TreeNode, level: int):
        """Set node levels recursively"""
        node.level = level
        for child in node.children:
            self._set_levels(child, level + 1)
    
    def _get_metadata(self) -> Dict[str, Any]:
        """Get metadata for the tree"""
        return {
            'build_timestamp': datetime.now().isoformat(),
            'builder_version': '1.0'
        }