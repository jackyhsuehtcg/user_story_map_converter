#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
團隊管理模組 - 處理團隊設定和並發控制
"""

import json
import os
import fcntl
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


class TeamManager:
    """團隊管理器，處理團隊設定和檔案鎖定"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.teams_config_file = "teams.json"
        self.lock_dir = "temp"
        self.exports_dir = "exports"
        self.logger = logging.getLogger(__name__)
        
        # 確保必要目錄存在
        os.makedirs(self.lock_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)
        
        # 載入團隊設定
        self.teams = self._load_teams()
    
    def _load_teams(self) -> Dict[str, Dict]:
        """載入團隊設定檔"""
        if os.path.exists(self.teams_config_file):
            try:
                with open(self.teams_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"載入團隊設定失敗: {e}")
                return {}
        return {}
    
    def _save_teams(self):
        """儲存團隊設定檔"""
        try:
            with open(self.teams_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.teams, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"儲存團隊設定失敗: {e}")
    
    def get_all_teams(self) -> List[Dict]:
        """獲取所有團隊列表，包含狀態資訊"""
        teams_list = []
        
        for team_id, team_config in self.teams.items():
            team_info = {
                'id': team_id,
                'name': team_config.get('name', f'Team {team_id}'),
                'lark_url': team_config.get('lark_url', ''),
                'description': team_config.get('description', ''),
                'created_at': team_config.get('created_at', ''),
                'status': self._get_team_status(team_id),
                'last_updated': self._get_last_updated(team_id),
                'record_count': self._get_record_count(team_id),
                'mindmap_file': self._get_mindmap_file(team_id)
            }
            teams_list.append(team_info)
        
        return teams_list
    
    def _get_team_status(self, team_id: str) -> str:
        """獲取團隊目前狀態"""
        lock_file = os.path.join(self.lock_dir, f".lock_{team_id}")
        
        if os.path.exists(lock_file):
            # 檢查鎖定檔案是否太舊（超過 10 分鐘視為無效）
            if time.time() - os.path.getmtime(lock_file) > 600:
                os.remove(lock_file)
                return "idle"
            return "generating"
        
        # 檢查是否有最新的心智圖檔案
        mindmap_file = self._get_mindmap_file(team_id)
        if mindmap_file:
            return "active"
        
        return "idle"
    
    def _get_last_updated(self, team_id: str) -> str:
        """獲取最後更新時間"""
        mindmap_file = self._get_mindmap_file(team_id)
        if mindmap_file:
            return mindmap_file['created_at']
        return ""
    
    def _get_record_count(self, team_id: str) -> int:
        """獲取記錄數（從團隊設定中讀取）"""
        team_config = self.teams.get(team_id, {})
        return team_config.get('record_count', 0)
    
    def _get_mindmap_file(self, team_id: str) -> Optional[Dict]:
        """獲取團隊的心智圖檔案（只保留最新的一個）"""
        if not os.path.exists(self.exports_dir):
            return None
        
        # 找出所有相關檔案
        files = []
        for filename in os.listdir(self.exports_dir):
            if filename.startswith(f"{team_id}_") and filename.endswith('.html'):
                file_path = os.path.join(self.exports_dir, filename)
                stat = os.stat(file_path)
                
                files.append({
                    'filename': filename,
                    'path': file_path,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                })
        
        if not files:
            return None
        
        # 只保留最新的檔案，刪除舊的
        sorted_files = sorted(files, key=lambda f: f['mtime'], reverse=True)
        latest_file = sorted_files[0]
        
        # 刪除舊檔案
        for old_file in sorted_files[1:]:
            try:
                os.remove(old_file['path'])
                self.logger.info(f"刪除舊心智圖檔案: {old_file['filename']}")
            except Exception as e:
                self.logger.error(f"刪除舊檔案失敗: {old_file['filename']}, 錯誤: {e}")
        
        return latest_file
    
    @contextmanager
    def team_lock(self, team_id: str):
        """團隊鎖定上下文管理器"""
        lock_file = os.path.join(self.lock_dir, f".lock_{team_id}")
        
        try:
            # 檢查是否已經被鎖定
            if os.path.exists(lock_file):
                # 檢查鎖定檔案是否太舊
                if time.time() - os.path.getmtime(lock_file) > 600:  # 10分鐘
                    os.remove(lock_file)
                else:
                    raise Exception("團隊正在處理中，請稍後再試")
            
            # 建立鎖定檔案
            with open(lock_file, 'w') as f:
                f.write(f"locked_by_pid_{os.getpid()}_at_{datetime.now().isoformat()}")
            
            yield
            
        finally:
            # 清理鎖定檔案
            if os.path.exists(lock_file):
                os.remove(lock_file)
    
    def add_team(self, team_data: Dict) -> Dict:
        """新增團隊"""
        team_id = team_data.get('id') or str(int(time.time()))
        
        team_config = {
            'name': team_data.get('name', ''),
            'lark_url': team_data.get('lark_url', ''),
            'description': team_data.get('description', ''),
            'record_count': 0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.teams[team_id] = team_config
        self._save_teams()
        
        return {
            'id': team_id,
            'message': '團隊新增成功',
            **team_config
        }
    
    def update_team(self, team_id: str, team_data: Dict) -> Dict:
        """更新團隊設定"""
        if team_id not in self.teams:
            return {'error': '團隊不存在'}
        
        # 檢查 URL 是否更改
        old_lark_url = self.teams[team_id].get('lark_url')
        new_lark_url = team_data.get('lark_url', old_lark_url)
        url_changed = old_lark_url != new_lark_url
        
        self.teams[team_id].update({
            'name': team_data.get('name', self.teams[team_id].get('name')),
            'lark_url': new_lark_url,
            'description': team_data.get('description', self.teams[team_id].get('description')),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # 如果 URL 更改，重置相關狀態
        if url_changed:
            self.logger.info(f"團隊 {team_id} 的 Lark URL 已更改，重置狀態")
            # 重置記錄數和清除心智圖檔案
            self.teams[team_id]['record_count'] = 0
            self._cleanup_team_files(team_id)
            # 移除任何現有的狀態標記
            if 'status' in self.teams[team_id]:
                del self.teams[team_id]['status']
        
        # 確保記錄數欄位存在
        if 'record_count' not in self.teams[team_id]:
            self.teams[team_id]['record_count'] = 0
        
        self._save_teams()
        
        return {
            'id': team_id,
            'message': '團隊更新成功',
            **self.teams[team_id]
        }
    
    def delete_team(self, team_id: str) -> Dict:
        """刪除團隊"""
        if team_id not in self.teams:
            return {'error': '團隊不存在'}
        
        # 檢查是否正在處理中
        if self._get_team_status(team_id) == "generating":
            return {'error': '團隊正在處理中，無法刪除'}
        
        # 刪除團隊設定
        del self.teams[team_id]
        self._save_teams()
        
        # 刪除相關檔案
        self._cleanup_team_files(team_id)
        
        return {'message': '團隊刪除成功'}
    
    def update_team_record_count(self, team_id: str, record_count: int):
        """更新團隊記錄數"""
        if team_id in self.teams:
            self.teams[team_id]['record_count'] = record_count
            self.teams[team_id]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_teams()
    
    def _cleanup_team_files(self, team_id: str):
        """清理團隊相關檔案"""
        # 清理匯出檔案
        if os.path.exists(self.exports_dir):
            for filename in os.listdir(self.exports_dir):
                if filename.startswith(f"{team_id}_"):
                    file_path = os.path.join(self.exports_dir, filename)
                    os.remove(file_path)
        
        # 清理暫存檔案
        if os.path.exists(self.lock_dir):
            for filename in os.listdir(self.lock_dir):
                if filename.startswith(f".lock_{team_id}") or filename.startswith(f"{team_id}_"):
                    file_path = os.path.join(self.lock_dir, filename)
                    os.remove(file_path)
    
    def get_team(self, team_id: str) -> Optional[Dict]:
        """獲取單一團隊資訊"""
        if team_id not in self.teams:
            return None
        
        team_config = self.teams[team_id]
        
        return {
            'id': team_id,
            'name': team_config.get('name', f'Team {team_id}'),
            'lark_url': team_config.get('lark_url', ''),
            'description': team_config.get('description', ''),
            'created_at': team_config.get('created_at', ''),
            'status': self._get_team_status(team_id),
            'last_updated': self._get_last_updated(team_id),
            'record_count': self._get_record_count(team_id),
            'mindmap_file': self._get_mindmap_file(team_id)
        }
    
    def is_team_busy(self, team_id: str) -> bool:
        """檢查團隊是否忙碌中"""
        return self._get_team_status(team_id) == "generating"
    
    def clear_team_mindmaps(self, team_id: str) -> Dict:
        """清空團隊的心智圖檔案"""
        if team_id not in self.teams:
            return {'error': '團隊不存在'}
        
        # 檢查是否正在處理中
        if self._get_team_status(team_id) == "generating":
            return {'error': '團隊正在處理中，無法清空心智圖'}
        
        cleared_count = 0
        
        # 清空匯出檔案
        if os.path.exists(self.exports_dir):
            for filename in os.listdir(self.exports_dir):
                if filename.startswith(f"{team_id}_"):
                    file_path = os.path.join(self.exports_dir, filename)
                    try:
                        os.remove(file_path)
                        cleared_count += 1
                    except Exception as e:
                        self.logger.error(f"刪除檔案失敗: {file_path}, 錯誤: {e}")
        
        # 重置記錄數（可選）
        if team_id in self.teams:
            self.teams[team_id]['record_count'] = 0
            self.teams[team_id]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_teams()
        
        return {
            'message': '心智圖清空成功',
            'cleared_count': cleared_count
        }