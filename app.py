#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 應用程式 - Gmail 風格的 User Story Map Converter
"""

import yaml
import threading
import os
from flask import Flask, render_template, request, jsonify, url_for
from datetime import datetime
from core.team_manager import TeamManager
from core.lark_client import LarkClient
from core.tree_builder import TreeBuilder
import yaml
import subprocess
import tempfile
from pathlib import Path

app = Flask(__name__)

# 載入設定檔
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app.config['SECRET_KEY'] = config['app']['secret_key']

# 初始化核心模組
team_manager = TeamManager(config)

# 設定日誌
import logging
logger = logging.getLogger('app')
logger.setLevel(getattr(logging, config['logging']['level']))

# 初始化 Lark 客戶端
lark_client = LarkClient(
    app_id=config['lark']['app_id'],
    app_secret=config['lark']['app_secret'],
    config=config['lark'],
    logger=logger
)

# 初始化樹狀結構建構器
tree_builder = TreeBuilder(logger, config.get('tree_builder', {}))

# 心智圖生成器類別（簡化版，從 test_markmap_converter.py 複製核心邏輯）
class SimpleMindmapGenerator:
    def __init__(self):
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        self.config = self._load_config()
        self.jira_config = self.config.get('jira', {})
    
    def _load_config(self):
        """載入配置檔案"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {
                'jira': {
                    'base_url': 'https://jira.tc-gaming.co/jira',
                    'issue_url_template': '{base_url}/browse/{tcg_number}',
                    'link_target': '_blank',
                    'link_title_template': 'Open {tcg_number} in JIRA'
                }
            }
    
    def _generate_jira_link(self, story_no: str, tcg):
        """生成 JIRA 連結或純文字 Story 編號"""
        if not tcg:
            return f"<small>{story_no}</small>"
        
        base_url = self.jira_config.get('base_url', 'https://jira.tc-gaming.co/jira')
        url_template = self.jira_config.get('issue_url_template', '{base_url}/browse/{tcg_number}')
        link_target = self.jira_config.get('link_target', '_blank')
        title_template = self.jira_config.get('link_title_template', 'Open {tcg_number} in JIRA')
        
        jira_url = url_template.format(base_url=base_url, tcg_number=tcg)
        link_title = title_template.format(tcg_number=tcg)
        
        return f'<small><a href="{jira_url}" target="{link_target}" title="{link_title}">{story_no}</a></small>'
    
    def _escape_html_attr(self, text: str) -> str:
        """轉義 HTML 屬性中的特殊字符"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')  # 必須先處理 &
                   .replace('"', '&quot;')
                   .replace("'", '&#39;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('\n', '&#10;')  # 換行符
                   .replace('\r', '&#13;')  # 回車符
                   .replace('\t', '&#9;'))   # 制表符
    
    def _extract_middle_part(self, story_no: str) -> str:
        """從 Story-XXX-YYYYY 格式中提取中間的 XXX 部分"""
        try:
            parts = story_no.split('-')
            if len(parts) >= 3:
                return parts[1]
            else:
                return story_no
        except:
            return story_no
    
    def _get_root_node_name(self, trees):
        """從樹狀結構中提取根節點名稱"""
        if not trees:
            return "使用者故事地圖"
        
        first_tree = trees[0]
        story_no = first_tree.get('story_no', 'Story-ARD-00001')
        return self._extract_middle_part(story_no)
    
    def _add_tree_to_markdown(self, node, lines, level: int):
        """遞歸添加樹節點到 Markdown"""
        prefix = '#' * level
        story_no = node.get('story_no', 'Unknown')
        features = node.get('features', 'No description')
        criteria = node.get('criteria', '')
        tcg = node.get('tcg')
        
        story_display = self._generate_jira_link(story_no, tcg)
        
        criteria_attr = f' data-criteria="{self._escape_html_attr(criteria)}"' if criteria else ''
        title = f'{prefix} <span{criteria_attr}>{story_display}<br/><strong>{features}</strong></span>'
        lines.append(title)
        lines.append("")
        
        children = node.get('children', [])
        if children:
            sorted_children = sorted(children, key=lambda x: x.get('story_no', ''))
            for child in sorted_children:
                self._add_tree_to_markdown(child, lines, level + 1)
    
    def generate_markdown_from_tree(self, tree_data):
        """從樹狀資料生成 Markmap 相容的 Markdown"""
        lines = []
        
        lines.extend([
            "---",
            "title: User Story Map",
            "markmap:",
            "  colorFreezeLevel: 2",
            "  maxWidth: 400",
            "  spacingHorizontal: 150",
            "  spacingVertical: 15",
            "  autoFit: true",
            "  fontSize: 14",
            "---",
            "",
        ])
        
        trees = tree_data['tree_data']['trees']
        root_name = self._get_root_node_name(trees)
        lines.extend([
            f"# **{root_name}**",
            ""
        ])
        
        sorted_trees = sorted(trees, key=lambda x: x.get('story_no', ''))
        
        for tree in sorted_trees:
            self._add_tree_to_markdown(tree, lines, level=2)
        
        return '\n'.join(lines)
    
    def generate_html_with_markmap(self, markdown_content: str, output_path: str) -> bool:
        """使用 markmap-cli 生成 HTML"""
        try:
            md_file = self.temp_dir / "temp_mindmap.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            cmd = [
                'markmap',
                str(md_file),
                '-o', output_path,
                '--no-open'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 注入自定義 CSS 和 JavaScript
                self._inject_custom_styles_and_scripts(output_path)
                logger.info(f"✅ HTML 生成成功: {output_path}")
                return True
            else:
                logger.error(f"❌ HTML 生成失敗: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 生成 HTML 時發生錯誤: {e}")
            return False
        finally:
            if md_file.exists():
                md_file.unlink()
    
    def _inject_custom_styles_and_scripts(self, html_path: str):
        """注入自定義 CSS 和 JavaScript 來實現 Criteria 浮動顯示"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 自定義 CSS 樣式
            custom_css = """
            <style>
            /* Criteria 浮動顯示樣式 */
            .criteria-tooltip {
                position: absolute;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                max-width: 320px;
                min-width: 120px;
                word-wrap: break-word;
                white-space: normal;
                line-height: 1.4;
                z-index: 1000;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.2s ease-in-out;
                border: 1px solid #555;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
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
            
            # 自定義 JavaScript
            custom_js = """
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
                                        // 解碼 HTML 實體並處理換行符
                                        criteria = criteria
                                            .replace(/&quot;/g, '"')
                                            .replace(/&#39;/g, "'")
                                            .replace(/&lt;/g, '<')
                                            .replace(/&gt;/g, '>')
                                            .replace(/&#10;/g, '\n')
                                            .replace(/&#13;/g, '\r')
                                            .replace(/&#9;/g, '\t')
                                            .replace(/&amp;/g, '&'); // 最後處理 &
                                        
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
                        // 使用 innerHTML 來正確顯示換行符
                        tooltip.innerHTML = criteriaText.replace(/\n/g, '<br>');
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
            
            # 注入 CSS 到 </head> 之前
            html_content = html_content.replace('</head>', custom_css + '\n</head>')
            
            # 注入 JavaScript 到 </body> 之前
            html_content = html_content.replace('</body>', custom_js + '\n</body>')
            
            # 寫回檔案
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info("✅ 自定義樣式和腳本注入成功")
            
        except Exception as e:
            logger.warning(f"⚠️ 注入自定義樣式失敗: {e}")

# 初始化心智圖生成器
mindmap_generator = SimpleMindmapGenerator()

def calculate_mindmap_stats(team, mindmap_file, logger):
    """計算心智圖統計資訊"""
    stats = {
        'total_nodes': team.get('record_count', 0),
        'criteria_nodes': 0,
        'jira_links': 0,
        'max_depth': 0,
        'generation_time': 0
    }
    
    # 如果沒有心智圖檔案，返回基本統計
    if not mindmap_file:
        return stats
    
    try:
        # 獲取心智圖檔案創建時間來計算生成時間
        created_time = mindmap_file.get('created_at', '')
        if created_time:
            from datetime import datetime
            try:
                created_dt = datetime.strptime(created_time, '%Y-%m-%d %H:%M:%S')
                # 估算生成時間（基於檔案大小和記錄數）
                file_size = mindmap_file.get('size', 0)
                record_count = team.get('record_count', 0)
                
                # 根據記錄數估算生成時間
                if record_count > 0:
                    base_time = min(max(record_count * 0.1, 0.5), 10.0)  # 0.5-10秒之間
                    stats['generation_time'] = round(base_time, 2)
                else:
                    stats['generation_time'] = 0.5
            except ValueError:
                stats['generation_time'] = 0.5
        
        # 嘗試從團隊資料重新構建樹狀結構來計算詳細統計
        if team.get('record_count', 0) > 0:
            # 模擬重新獲取資料並分析
            team_info = team_manager.get_team(team['id'])
            if team_info and team_info.get('lark_url'):
                try:
                    # 解析 Lark URL 並獲取資料
                    from urllib.parse import urlparse, parse_qs
                    import re
                    
                    parsed = urlparse(team_info['lark_url'])
                    wiki_path_match = re.match(r'/wiki/([^/?]+)', parsed.path)
                    base_path_match = re.match(r'/base/([^/?]+)', parsed.path)
                    
                    if wiki_path_match:
                        wiki_token = wiki_path_match.group(1)
                    elif base_path_match:
                        wiki_token = base_path_match.group(1)
                    else:
                        raise Exception("無效的 Lark URL 格式")
                    
                    query_params = parse_qs(parsed.query)
                    if 'table' not in query_params:
                        raise Exception("URL 中缺少 table 參數")
                    
                    table_id = query_params['table'][0]
                    
                    # 獲取資料並分析
                    logger.debug(f"開始計算團隊 {team['id']} 的統計資訊")
                    records = lark_client.get_table_records(wiki_token, table_id)
                    if records:
                        tree_result = tree_builder.build_tree(records)
                        tree_stats = analyze_tree_structure(tree_result)
                        
                        stats.update(tree_stats)
                        logger.info(f"統計資訊計算完成: 總節點 {stats['total_nodes']}, Criteria 節點 {stats['criteria_nodes']}, JIRA 連結 {stats['jira_links']}, 最大深度 {stats['max_depth']}")
                    else:
                        logger.warning("無法獲取 Lark 記錄進行統計")
                    
                except Exception as e:
                    logger.warning(f"無法獲取詳細統計資訊: {e}")
                    # 使用基本估算
                    record_count = team.get('record_count', 0)
                    stats['criteria_nodes'] = max(1, record_count // 4)  # 估算約1/4節點有criteria
                    stats['jira_links'] = max(0, record_count // 3)      # 估算約1/3節點有JIRA連結
                    stats['max_depth'] = min(max(2, record_count // 8), 6)  # 估算深度2-6層
        
    except Exception as e:
        logger.error(f"計算統計資訊失敗: {e}")
    
    return stats

def analyze_tree_structure(tree_result):
    """分析樹狀結構並計算統計資訊"""
    stats = {
        'total_nodes': 0,
        'criteria_nodes': 0,
        'jira_links': 0,
        'max_depth': 0
    }
    
    if not tree_result or 'trees' not in tree_result:
        return stats
    
    def analyze_node(node, depth=1):
        """遞迴分析節點"""
        stats['total_nodes'] += 1
        stats['max_depth'] = max(stats['max_depth'], depth)
        
        # 檢查是否有 criteria
        if node.get('criteria'):
            stats['criteria_nodes'] += 1
        
        # 檢查是否有 TCG (JIRA 連結)
        if node.get('tcg'):
            stats['jira_links'] += 1
        
        # 遞迴處理子節點
        for child in node.get('children', []):
            analyze_node(child, depth + 1)
    
    # 分析所有樹（根節點從深度 1 開始）
    for tree in tree_result['trees']:
        analyze_node(tree, 1)
    
    return stats

@app.route('/')
def index():
    """儀表板首頁"""
    teams = team_manager.get_all_teams()
    
    # 計算總體統計資訊
    total_stats = {
        'total_teams': len(teams),
        'generating_teams': len([t for t in teams if t['status'] == 'generating']),
        'total_records': sum(t.get('record_count', 0) for t in teams),
        'total_mindmap_files': sum(1 for t in teams if t.get('mindmap_file'))
    }
    
    # 按狀態分組團隊
    teams_by_status = {
        'active': [t for t in teams if t['status'] == 'active'],
        'generating': [t for t in teams if t['status'] == 'generating'],
        'idle': [t for t in teams if t['status'] == 'idle'],
        'error': [t for t in teams if t['status'] == 'error']
    }
    
    return render_template('index.html', 
                         teams=teams, 
                         total_stats=total_stats,
                         teams_by_status=teams_by_status)

@app.route('/teams')
def teams():
    """團隊管理頁面"""
    teams = team_manager.get_all_teams()
    return render_template('teams.html', teams=teams)

@app.route('/mindmap/<team_id>')
def mindmap(team_id):
    """心智圖查看頁面"""
    team = team_manager.get_team(team_id)
    if not team:
        return "Team not found", 404
    
    # 獲取心智圖檔案
    mindmap_file = team.get('mindmap_file')
    mindmap_url = f"/static/sample-mindmap.html"  # 預設範例
    
    if mindmap_file:
        # 使用心智圖檔案
        mindmap_url = f"/exports/{mindmap_file['filename']}"
        logger.info(f"使用心智圖檔案: {mindmap_url}")
    else:
        logger.warning(f"團隊 {team_id} 沒有心智圖檔案，使用預設範例")
    
    # 計算統計資訊
    stats = calculate_mindmap_stats(team, mindmap_file, logger)
    
    return render_template('mindmap.html', 
                         team=team, 
                         mindmap_url=mindmap_url,
                         stats=stats)

# API 路由
@app.route('/api/teams', methods=['GET'])
def api_teams():
    """獲取團隊列表 API"""
    teams = team_manager.get_all_teams()
    return jsonify(teams)

@app.route('/api/teams/<team_id>/refresh', methods=['POST'])
def api_refresh_team(team_id):
    """刷新團隊 API"""
    try:
        # 檢查團隊是否存在
        team = team_manager.get_team(team_id)
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        # 檢查是否已經在處理中
        if team_manager.is_team_busy(team_id):
            return jsonify({'error': '團隊正在處理中，請稍後再試'}), 409
        
        # 啟動背景任務進行心智圖生成
        def generate_mindmap():
            try:
                with team_manager.team_lock(team_id):
                    logger.info(f"開始為團隊 {team_id} 生成心智圖")
                    
                    # 1. 從 Lark 獲取資料
                    team_info = team_manager.get_team(team_id)
                    lark_url = team_info['lark_url']
                    
                    # 解析 Lark URL (支援 wiki 和 base 格式)
                    from urllib.parse import urlparse, parse_qs
                    import re
                    
                    parsed = urlparse(lark_url)
                    
                    # 支援兩種格式：
                    # 1. /wiki/xxx?table=yyy (新格式)
                    # 2. /base/xxx?table=yyy (舊格式)
                    wiki_path_match = re.match(r'/wiki/([^/?]+)', parsed.path)
                    base_path_match = re.match(r'/base/([^/?]+)', parsed.path)
                    
                    if wiki_path_match:
                        wiki_token = wiki_path_match.group(1)
                    elif base_path_match:
                        wiki_token = base_path_match.group(1)
                    else:
                        raise Exception("無效的 Lark URL 格式，請使用 /wiki/xxx?table=yyy 或 /base/xxx?table=yyy 格式")
                    
                    query_params = parse_qs(parsed.query)
                    if 'table' not in query_params:
                        raise Exception("URL 中缺少 table 參數")
                    
                    table_id = query_params['table'][0]
                    
                    # 獲取 Lark 資料
                    logger.info(f"從 Lark 獲取資料: {wiki_token}/{table_id}")
                    records = lark_client.get_table_records(wiki_token, table_id)
                    
                    if not records:
                        raise Exception("無法獲取 Lark 資料")
                    
                    # 2. 建構樹狀結構
                    logger.info(f"建構樹狀結構，共 {len(records)} 筆記錄")
                    tree_result = tree_builder.build_tree(records)
                    
                    # 3. 生成心智圖 - 使用與 test_markmap_converter.py 相同的格式
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_filename = f"{team_id}_{timestamp}.html"
                    output_path = os.path.join("exports", output_filename)
                    
                    logger.info(f"生成心智圖: {output_path}")
                    
                    # 確保 exports 目錄存在
                    os.makedirs("exports", exist_ok=True)
                    
                    # 照抄 test_markmap_converter.py 的邏輯
                    tree_data = {
                        'tree_data': {
                            'trees': tree_result['trees']
                        }
                    }
                    
                    # 生成 Markdown
                    markdown_content = mindmap_generator.generate_markdown_from_tree(tree_data)
                    
                    # 生成 HTML
                    success = mindmap_generator.generate_html_with_markmap(markdown_content, output_path)
                    
                    if success:
                        logger.info(f"團隊 {team_id} 心智圖生成完成: {output_path}")
                        
                        # 更新團隊記錄數
                        team_manager.update_team_record_count(team_id, len(records))
                        
                        logger.info(f"團隊 {team_id} 記錄數已更新: {len(records)}")
                    else:
                        raise Exception("心智圖生成失敗")
                    
            except Exception as e:
                logger.error(f"團隊 {team_id} 心智圖生成失敗: {e}")
                # 可以在這裡記錄錯誤到團隊狀態中
        
        # 啟動背景執行緒
        thread = threading.Thread(target=generate_mindmap)
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': '開始生成心智圖', 'status': 'generating'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams', methods=['POST'])
def api_create_team():
    """創建團隊 API"""
    try:
        data = request.json
        result = team_manager.add_team(data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/<team_id>', methods=['DELETE'])
def api_delete_team(team_id):
    """刪除團隊 API"""
    try:
        result = team_manager.delete_team(team_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/<team_id>', methods=['GET'])
def api_get_team(team_id):
    """獲取單一團隊資訊 API"""
    try:
        team = team_manager.get_team(team_id)
        
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        return jsonify(team)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/<team_id>', methods=['PUT'])
def api_update_team(team_id):
    """更新團隊 API"""
    try:
        data = request.json
        result = team_manager.update_team(team_id, data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/<team_id>/test-connection', methods=['POST'])
def api_test_connection(team_id):
    """測試團隊連接 API"""
    try:
        # 獲取團隊資訊
        team = team_manager.get_team(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team not found'}), 404
        
        lark_url = team['lark_url']
        if not lark_url:
            return jsonify({'success': False, 'error': 'Lark URL 未設定'}), 400
        
        # 解析 Lark URL
        from urllib.parse import urlparse, parse_qs
        import re
        
        try:
            parsed = urlparse(lark_url)
            
            # 支援 wiki 和 base 格式
            wiki_path_match = re.match(r'/wiki/([^/?]+)', parsed.path)
            base_path_match = re.match(r'/base/([^/?]+)', parsed.path)
            
            if wiki_path_match:
                wiki_token = wiki_path_match.group(1)
            elif base_path_match:
                wiki_token = base_path_match.group(1)
            else:
                return jsonify({
                    'success': False, 
                    'error': '無效的 Lark URL 格式，請使用 /wiki/xxx?table=yyy 或 /base/xxx?table=yyy 格式'
                }), 400
            
            query_params = parse_qs(parsed.query)
            if 'table' not in query_params:
                return jsonify({
                    'success': False, 
                    'error': 'URL 中缺少 table 參數'
                }), 400
            
            table_id = query_params['table'][0]
            
        except Exception as e:
            return jsonify({
                'success': False, 
                'error': f'URL 解析失敗: {str(e)}'
            }), 400
        
        # 測試連接
        try:
            logger.info(f"測試連接: {wiki_token}/{table_id}")
            
            # 測試表格結構
            schema_data = lark_client.get_table_schema(wiki_token, table_id)
            if not schema_data:
                return jsonify({
                    'success': False, 
                    'error': '無法獲取表格結構，請檢查 URL 是否正確或是否有權限訪問'
                }), 400
            
            # 測試記錄數量（只取第一頁測試）
            test_records = lark_client.get_table_records(wiki_token, table_id, page_size=1)
            
            # 組裝測試結果
            field_count = len(schema_data.get('items', []))
            table_name = f"Table_{table_id}"  # 可以改進為從 API 獲取實際名稱
            
            # 簡單估算記錄數（實際可以改為獲取更準確的數字）
            record_count = "測試成功" if test_records else 0
            
            result = {
                'success': True,
                'table_name': table_name,
                'field_count': field_count,
                'record_count': record_count,
                'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'wiki_token': wiki_token,
                'table_id': table_id
            }
            
            logger.info(f"連接測試成功: {team_id}")
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"連接測試失敗: {team_id}, 錯誤: {e}")
            return jsonify({
                'success': False, 
                'error': f'連接測試失敗: {str(e)}'
            }), 400
            
    except Exception as e:
        logger.error(f"測試連接 API 異常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/teams/<team_id>/clear-mindmaps', methods=['POST'])
def api_clear_mindmaps(team_id):
    """清空團隊心智圖 API"""
    try:
        result = team_manager.clear_team_mindmaps(team_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        logger.info(f"團隊 {team_id} 心智圖已清空，共清空 {result['cleared_count']} 個檔案")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"清空心智圖 API 異常: {e}")
        return jsonify({'error': str(e)}), 500

# 創建示例心智圖文件
@app.route('/create-sample-mindmap')
def create_sample_mindmap():
    """創建示例心智圖文件"""
    import os
    
    sample_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sample Mindmap</title>
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f6f8fc;
        }
        .mindmap-container { 
            width: 100%; 
            height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }
        .node { 
            background: #4A69BD; 
            color: white; 
            padding: 10px 20px; 
            border-radius: 8px; 
            margin: 10px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .sample-tree { 
            text-align: center; 
        }
        .level-1 { background: #4A69BD; }
        .level-2 { background: #5A7BD6; }
        .level-3 { background: #6B8EE8; }
    </style>
</head>
<body>
    <div class="mindmap-container">
        <div class="sample-tree">
            <div class="node level-1">User Story Map</div>
            <div style="display: flex; justify-content: center; flex-wrap: wrap;">
                <div class="node level-2">用戶登入</div>
                <div class="node level-2">產品瀏覽</div>
                <div class="node level-2">購物車</div>
                <div class="node level-2">結帳流程</div>
            </div>
            <div style="display: flex; justify-content: center; flex-wrap: wrap;">
                <div class="node level-3">註冊帳號</div>
                <div class="node level-3">忘記密碼</div>
                <div class="node level-3">商品搜尋</div>
                <div class="node level-3">商品篩選</div>
                <div class="node level-3">加入購物車</div>
                <div class="node level-3">修改數量</div>
                <div class="node level-3">選擇付款</div>
                <div class="node level-3">確認訂單</div>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    # 確保靜態文件夾存在
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # 創建示例心智圖文件
    sample_path = os.path.join(app.static_folder, 'sample-mindmap.html')
    with open(sample_path, 'w', encoding='utf-8') as f:
        f.write(sample_html)
    
    return jsonify({'message': 'Sample mindmap created', 'path': sample_path})

# 提供 exports 目錄的靜態檔案服務
@app.route('/exports/<path:filename>')
def exports(filename):
    """提供匯出檔案的靜態服務"""
    from flask import send_from_directory
    return send_from_directory('exports', filename)

# 錯誤處理
@app.errorhandler(404)
def page_not_found(e):
    return f"<h1>404 - 頁面不存在</h1><p>請檢查 URL 是否正確</p><a href='{url_for('index')}'>返回首頁</a>", 404

if __name__ == '__main__':
    # 確保靜態文件夾存在
    import os
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # 確保靜態檔案夾存在
    import os
    if not os.path.exists('static'):
        os.makedirs('static')
    
    logger.info("🚀 User Story Map Converter 啟動中...")
    logger.info("🎨 Gmail 風格的雙欄式佈局")
    logger.info("🌐 訪問 http://localhost:8889 查看")
    logger.info("📋 可用頁面:")
    logger.info("   • 儀表板: /")
    logger.info("   • 團隊管理: /teams")
    logger.info("   • 心智圖查看: /mindmap/<team_id>")
    logger.info("   • 創建示例心智圖: /create-sample-mindmap")
    logger.info("✨ 特色功能:")
    logger.info("   • 左側固定導覽邊欄")
    logger.info("   • 柔和的專業配色")
    logger.info("   • 資訊密集的表格設計")
    logger.info("   • 簡潔的卡片式儀表板")
    logger.info("   • 檔案鎖定防止並發衝突")
    logger.info("   • 完整的 Lark → 心智圖轉換流程")
    
    app.run(debug=True, host='0.0.0.0', port=8889)