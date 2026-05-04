#!/usr/bin/env python3
"""
输出格式化模块
支持多种输出格式和美化显示
"""

import datetime
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import arxiv
from jinja2 import Environment, FileSystemLoader, Template

from ..utils.logger import logger


class OutputFormatter:
    """输出格式化器"""

    def __init__(self, templates_dir: Path, github_repo_url: str = None):
        """
        初始化格式化器

        Args:
            templates_dir: 模板目录路径
            github_repo_url: GitHub仓库URL
        """
        self.templates_dir = templates_dir
        self.github_repo_url = github_repo_url or "https://github.com/your-username/hermes4arxiv"
        self.env = Environment(loader=FileSystemLoader(str(templates_dir)))

    def format_markdown(
        self, papers_analyses: List[Tuple[arxiv.Result, Dict[str, Any]]], title: str = None
    ) -> str:
        """
        格式化为Markdown格式

        Args:
            papers_analyses: 论文分析结果列表，每个元素为(paper, analysis_dict)
            title: 标题

        Returns:
            Markdown格式的内容
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        if title is None:
            title = f"Hermes4ArXiv 学术精华 ({today})"

        content = f"# {title}\n\n"
        content += f"**生成时间**: {today}\n"
        content += f"**论文数量**: {len(papers_analyses)}\n\n"

        for i, (paper, analysis_result) in enumerate(papers_analyses, 1):
            author_names = [author.name for author in paper.authors]
            
            # 处理分析内容 - 从字典中提取实际分析文本
            if isinstance(analysis_result, dict):
                analysis_text = analysis_result.get('analysis', '分析暂时不可用')
            else:
                analysis_text = analysis_result or '分析暂时不可用'

            content += f"## {i}. {paper.title}\n\n"
            content += f"**👥 作者**: {', '.join(author_names)}\n\n"
            content += f"**🏷️ 类别**: {', '.join(paper.categories)}\n\n"
            content += f"**📅 发布日期**: {paper.published.strftime('%Y-%m-%d')}\n\n"
            content += f"**🔗 链接**: [{paper.entry_id}]({paper.entry_id})\n\n"
            content += f"### 📝 分析结果\n\n{analysis_text}\n\n"
            content += "---\n\n"

        return content

    def format_html_email(self, papers_analyses: List[Tuple[arxiv.Result, Dict[str, Any]]]) -> str:
        """
        格式化为HTML邮件格式

        Args:
            papers_analyses: 论文分析结果列表，每个元素为(paper, analysis_dict)

        Returns:
            HTML格式的邮件内容
        """
        try:
            template = self.env.get_template("email_template.html")
        except Exception as e:
            logger.error(f"加载邮件模板失败: {e}")
            return self._fallback_html_format(papers_analyses)

        today = datetime.datetime.now().strftime("%Y年%m月%d日")

        # 准备模板数据
        papers_data = []
        categories_set = set()

        for paper, analysis_result in papers_analyses:
            author_names = [author.name for author in paper.authors]
            categories_set.update(paper.categories)

            # 处理分析内容 - 从字典中提取实际分析文本
            if isinstance(analysis_result, dict):
                # 优先使用html_analysis，如果不存在则使用analysis
                if 'html_analysis' in analysis_result and analysis_result['html_analysis']:
                    analysis_html = analysis_result['html_analysis']
                else:
                    analysis_text = analysis_result.get('analysis', '分析暂时不可用')
                    analysis_html = self._convert_analysis_to_html(analysis_text)
            else:
                # 兼容旧格式，直接是字符串
                analysis_html = self._convert_analysis_to_html(analysis_result)

            # 生成PDF链接
            pdf_url = paper.pdf_url if hasattr(paper, 'pdf_url') else paper.entry_id.replace('/abs/', '/pdf/') + '.pdf'

            papers_data.append(
                {
                    "title": paper.title,
                    "authors": ", ".join(author_names),
                    "published": paper.published.strftime("%Y年%m月%d日"),
                    "categories": paper.categories,
                    "url": paper.entry_id,
                    "pdf_url": pdf_url,
                    "analysis": analysis_html,
                }
            )

        template_data = {
            "date": today,
            "paper_count": len(papers_analyses),
            "categories": ", ".join(sorted(categories_set)),
            "papers": papers_data,
            "github_repo_url": self.github_repo_url,
        }

        return template.render(**template_data)

    def _convert_analysis_to_html(self, analysis: str) -> str:
        """
        将分析内容转换为HTML格式，支持五维分析结构

        Args:
            analysis: 分析内容

        Returns:
            HTML格式的分析内容
        """
        # 定义分析维度的图标映射
        dimension_icons = {
            "核心贡献": "🎯",
            "技术方法": "🔧", 
            "实验验证": "🧪",
            "影响与意义": "💡",
            "影响意义": "💡",
            "局限与展望": "🔮",
            "局限展望": "🔮",
            "Core Contribution": "🎯",
            "Technical Methods": "🔧",
            "Experimental Validation": "🧪", 
            "Impact & Significance": "💡",
            "Limitations & Future Work": "🔮"
        }

        # 首先尝试按行分割（适配新的格式：每个维度一行）
        lines = analysis.split("\n")
        html_sections = []

        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是新的分析维度
            is_dimension_title = False
            dimension_icon = "📝"
            dimension_title = ""
            
            # 匹配格式1: "🎯 **核心贡献**：内容" 或 "🎯 **核心贡献**: 内容"
            match1 = re.match(r'^([🎯🔧🧪💡🔮⭐📝])\s*\*\*(.+?)\*\*[:：]\s*(.+)$', line)
            if match1:
                emoji_in_text = match1.group(1).strip()
                dimension_title = match1.group(2).strip()
                content_text = match1.group(3).strip()
                
                # 首先使用文本中的 emoji
                dimension_icon = emoji_in_text
                
                # 如果能在字典中找到对应的图标，使用字典中的图标
                for dim_name, icon in dimension_icons.items():
                    if dim_name in dimension_title:
                        dimension_icon = icon
                        break
                
                is_dimension_title = True
                
                # 保存之前的section
                if current_section and current_content:
                    html_sections.append(self._create_analysis_section(current_section, current_content))
                
                # 创建新section，并直接添加内容
                current_section = {
                    "title": dimension_title,
                    "icon": dimension_icon
                }
                current_content = [content_text] if content_text else []
                continue
            
            # 匹配格式2: "⭐ **3.5星**：内容" (评分行)
            match2 = re.match(r'^[⭐]\s*\*\*(.+?)\*\*[:：]\s*(.+)$', line)
            if match2:
                rating_text = match2.group(1).strip()
                content_text = match2.group(2).strip()
                
                # 保存之前的section
                if current_section and current_content:
                    html_sections.append(self._create_analysis_section(current_section, current_content))
                
                # 创建评分section
                current_section = {
                    "title": rating_text,
                    "icon": "⭐"
                }
                current_content = [content_text] if content_text else []
                continue
            
            # 匹配格式3: 数字开头的标题 (如 "1. 核心贡献")
            match3 = re.match(r'^(\d+)\.\s*(.+?)[:：]?\s*$', line)
            if match3:
                dimension_title = match3.group(2).strip()
                dimension_icon = dimension_icons.get(dimension_title, "📝")
                is_dimension_title = True
                
                # 保存之前的section
                if current_section and current_content:
                    html_sections.append(self._create_analysis_section(current_section, current_content))
                
                # 开始新的section
                current_section = {
                    "title": dimension_title,
                    "icon": dimension_icon
                }
                current_content = []
                continue
            
            # 匹配格式4: 直接以维度名称开头
            for dim_name, icon in dimension_icons.items():
                if line.startswith(dim_name):
                    dimension_icon = icon
                    is_dimension_title = True
                    dimension_title = line
                    break
            
            if is_dimension_title and not match1 and not match2:
                # 保存之前的section
                if current_section and current_content:
                    html_sections.append(self._create_analysis_section(current_section, current_content))
                
                # 开始新的section
                current_section = {
                    "title": dimension_title,
                    "icon": dimension_icon
                }
                current_content = []
            else:
                # 添加到当前section的内容
                if line and not is_dimension_title:
                    current_content.append(line)

        # 添加最后一个section
        if current_section and current_content:
            html_sections.append(self._create_analysis_section(current_section, current_content))

        # 如果没有找到结构化的分析，使用简单格式
        if not html_sections:
            # 简单地将整个文本转换为HTML格式，处理换行和基本格式
            formatted_text = self._format_simple_text(analysis)
            return f'<div class="analysis-content">{formatted_text}</div>'

        return "\n".join(html_sections)

    def _create_analysis_section(self, section_info: Dict, content_list: List[str]) -> str:
        """
        创建分析section的HTML

        Args:
            section_info: section信息，包含title和icon
            content_list: 内容列表

        Returns:
            HTML section
        """
        title = section_info["title"]
        icon = section_info["icon"]
        
        # 处理内容 - 将所有内容合并为一个段落
        # 因为AI输出的每个维度通常是一个完整的段落
        if content_list:
            # 合并所有内容行
            full_content = " ".join(content_list)
            formatted_content = self._format_simple_text(full_content)
            content_str = f"<p>{formatted_content}</p>"
        else:
            content_str = ""

        return f'''<div class="analysis-section">
    <div class="analysis-title">
        <span class="icon-badge">{icon}</span>
        <strong>{title}</strong>
    </div>
    <div class="analysis-content">
        {content_str}
    </div>
</div>'''

    def _format_simple_text(self, text: str) -> str:
        """
        格式化简单文本，处理粗体、斜体等

        Args:
            text: 原始文本

        Returns:
            格式化后的HTML文本
        """
        if not text:
            return ""
        
        # 处理粗体 **text**
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # 处理斜体 *text* (但不匹配已经转换过的粗体)
        text = re.sub(r'(?<!\*)\*([^\*]+?)\*(?!\*)', r'<em>\1</em>', text)
        
        # 处理代码 `code`
        text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
        
        # 不自动转换所有换行，只保留双换行作为段落分隔
        # 单个换行保留为空格（方便长段落自然流动）
        text = text.replace('\n\n', '</p><p>')
        text = text.replace('\n', ' ')
        
        return text

    def _fallback_html_format(
        self, papers_analyses: List[Tuple[arxiv.Result, Dict[str, Any]]]
    ) -> str:
        """
        备用HTML格式化方法

        Args:
            papers_analyses: 论文分析结果列表

        Returns:
            简单的HTML格式内容
        """
        today = datetime.datetime.now().strftime("%Y年%m月%d日")

        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Hermes4ArXiv - 今日学术精华</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    line-height: 1.6; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    background: #f5f7fa;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 12px;
                    margin-bottom: 30px;
                }}
                .paper {{ 
                    background: white;
                    border: 1px solid #e9ecef; 
                    margin-bottom: 25px; 
                    padding: 25px; 
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                }}
                .paper-title {{ 
                    color: #2c3e50; 
                    font-size: 20px; 
                    font-weight: 600; 
                    margin-bottom: 15px; 
                    line-height: 1.4;
                }}
                .paper-meta {{ 
                    color: #6c757d; 
                    margin-bottom: 20px; 
                    font-size: 14px;
                }}
                .analysis {{ 
                    margin-top: 20px; 
                    line-height: 1.6;
                }}
                .paper-link {{
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                    color: white;
                    padding: 12px 20px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 600;
                    box-shadow: 0 2px 8px rgba(0, 123, 255, 0.25);
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                    margin-top: 15px;
                    margin-right: 10px;
                }}
                .paper-link:hover {{
                    background: linear-gradient(135deg, #0056b3 0%, #004494 100%);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 16px rgba(0, 123, 255, 0.35);
                    text-decoration: none;
                    color: white;
                }}
                .paper-link:active {{
                    transform: translateY(0);
                    box-shadow: 0 2px 8px rgba(0, 123, 255, 0.25);
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏛️ Hermes4ArXiv</h1>
                <p>赫尔墨斯为您送达今日学术精华</p>
                <p>{today}</p>
            </div>
            <div style="text-align: center; margin-bottom: 30px;">
                <p><strong>今日共分析 {len(papers_analyses)} 篇论文</strong></p>
            </div>
        """

        for i, (paper, analysis_result) in enumerate(papers_analyses, 1):
            author_names = [author.name for author in paper.authors]
            pdf_url = paper.entry_id.replace('/abs/', '/pdf/') + '.pdf'
            
            # 处理分析内容 - 从字典中提取实际分析文本
            if isinstance(analysis_result, dict):
                analysis_text = analysis_result.get('analysis', '分析暂时不可用')
            else:
                analysis_text = analysis_result or '分析暂时不可用'

            html += f"""
            <div class="paper">
                <div class="paper-title">{i}. {paper.title}</div>
                <div class="paper-meta">
                    <strong>👥 作者</strong>: {', '.join(author_names)}<br>
                    <strong>🏷️ 类别</strong>: {', '.join(paper.categories)}<br>
                    <strong>📅 发布日期</strong>: {paper.published.strftime('%Y年%m月%d日')}<br>
                </div>
                <div class="analysis">{analysis_text.replace(chr(10), '<br>')}</div>
                <div>
                    <a href="{paper.entry_id}" class="paper-link">🔗 查看原文</a>
                    <a href="{pdf_url}" class="paper-link">📄 下载PDF</a>
                </div>
            </div>
            """

        html += """
            <div style="text-align: center; margin-top: 40px; color: #6c757d; font-size: 14px;">
                <p>🏛️ Hermes4ArXiv - 智慧信使赫尔墨斯，每日为您传递学术前沿</p>
            </div>
        </body>
        </html>
        """

        return html

    def save_to_file(self, content: str, file_path: Path, mode: str = "a") -> None:
        """
        保存内容到文件

        Args:
            content: 要保存的内容
            file_path: 文件路径
            mode: 文件打开模式
        """
        try:
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)
            logger.info(f"内容已保存到 {file_path}")
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")

    def get_email_subject(self) -> str:
        """
        生成邮件主题

        Returns:
            邮件主题字符串
        """
        today = datetime.datetime.now().strftime("%Y年%m月%d日")
        return f"🏛️ Hermes4ArXiv - {today} AI论文分析报告"

    def create_summary_stats(
        self, papers_analyses: List[Tuple[arxiv.Result, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        创建统计摘要

        Args:
            papers_analyses: 论文分析结果列表

        Returns:
            统计信息字典
        """
        if not papers_analyses:
            return {}

        categories = {}
        authors = set()
        dates = []

        for paper, analysis_result in papers_analyses:
            # 统计类别
            for cat in paper.categories:
                categories[cat] = categories.get(cat, 0) + 1

            # 统计作者
            for author in paper.authors:
                authors.add(author.name)

            # 统计日期
            dates.append(paper.published.date())

        return {
            "total_papers": len(papers_analyses),
            "categories": categories,
            "unique_authors": len(authors),
            "date_range": {
                "earliest": min(dates) if dates else None,
                "latest": max(dates) if dates else None,
            },
        }
