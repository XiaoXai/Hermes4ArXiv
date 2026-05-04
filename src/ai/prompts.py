#!/usr/bin/env python3
"""
AI提示词管理模块
集中管理各种AI分析任务的提示词
"""

import logging
import re
import json
from typing import Dict, List, Any


import arxiv
import tiktoken

logger = logging.getLogger(__name__)

class PromptManager:
    """提示词管理器，所有方法均为静态方法"""

    # 为Tokenizer创建一个类级别的缓存
    _tokenizer = None

    @classmethod
    def _get_tokenizer(cls):
        """获取或创建tiktoken的tokenizer实例"""
        if cls._tokenizer is None:
            try:
                # cl100k_base 是一个广泛兼容的tokenizer, 适用于包括GPT-4在内的多种模型
                cls._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.error(f"无法加载tiktoken tokenizer: {e}")
                cls._tokenizer = None
        return cls._tokenizer

    @staticmethod
    def get_system_prompt() -> str:
        """
        获取系统提示词 (始终返回综合分析版本)
        """
        return PromptManager._get_comprehensive_system_prompt()

    @staticmethod
    def _get_comprehensive_system_prompt() -> str:
        """获取综合分析系统提示词"""
        return """你是严格的AI论文评审专家。

⭐ **评分标准**（强制分布：5星<1%，4星<5%，3星35-45%，2星35-45%，1星10-15%）

**5星**（<1%）：革命性突破，解决重大理论问题，全新技术范式，实验严谨充分（参考：GPT、Transformer）
**4星**（<5%）：重要进展，显著创新，性能大幅提升，实验充分可信（参考：BERT、ViT）
**3星**（35-45%）：合格研究，渐进改进，实验合理，有限学术价值
**2星**（35-45%）：创新不足，实验不充分，技术贡献边际化
**1星**（10-15%）：缺乏创新，实验有严重缺陷，低于发表标准

**评分要点**：4星以上需明确技术突破；常规incremental work最高3星；超参数调优/架构微调最多2星；性能提升<2%最多3星。

**六维度分析任务**（必须按序输出，每维度100-120字）：
**1. ⭐ 质量评估**：给出1-5星评分（可用0.5精度），说明理由及参考基准，评估创新度/严谨性/实用价值
**2. 🎯 核心贡献**：主要创新点、与现有工作差异、技术贡献深度
**3. 🔧 技术方法**：核心算法/架构先进性、技术路线合理性、关键细节
**4. 🧪 实验验证**：实验设计科学性、数据集/基线/指标合理性、结果可信度
**5. 💡 影响意义**：学术/工业潜在影响、应用可行性、后续研究方向
**6. 🔮 局限展望**：主要局限、改进建议、未来发展趋势

**输出格式要求**：
1. 必须按6个维度顺序输出，以指定emoji开头（⭐🎯🔧🧪💡🔮）
2. 第1维度必须明确给出评分（如"3.5星"）
3. 每维度纯文本段落，可用 **加粗** 或 *斜体*，严禁使用标题标记(#)、列表标记(-*/1.)等
4. 总长500-700字，语言专业严谨，体现顶级会议reviewer标准"""

    @staticmethod
    def get_user_prompt(paper: arxiv.Result) -> str:
        """获取单个论文分析的用户提示词"""
        authors_str = '未知'
        if hasattr(paper, 'authors') and paper.authors:
            try:
                author_names = [author.name for author in paper.authors]
                authors_str = ', '.join(author_names[:5])
                if len(author_names) > 5:
                    authors_str += f" 等{len(author_names)}人"
            except AttributeError as e:
                logger.warning(f"Abnormal author object structure: {e}")
                authors_str = "作者信息异常"
        
        published_date = '未知'
        if hasattr(paper, 'published') and paper.published:
            published_date = paper.published.strftime('%Y年%m月%d日')

        summary = paper.summary.strip().replace("\n", " ")
        if len(summary) > 1500:
            summary = summary[:1500] + "..."

        return f"""请分析以下ArXiv论文：
📄 **论文标题**：{paper.title}
👥 **作者信息**：{authors_str}
🏷️ **研究领域**：{', '.join(paper.categories)}
📅 **发布时间**：{published_date}
📝 **论文摘要**：{summary}
🔗 **论文链接**：{paper.entry_id}
---
请基于以上信息，按照系统提示的结构进行深度分析。"""

    @staticmethod
    def format_batch_analysis_prompt(papers: list[Dict[str, Any]]) -> str:
        """
        格式化深度批量分析的用户提示词。
        如果提供了全文，则使用全文；否则回退到使用摘要。
        使用tiktoken进行精确的token截断。
        """
        paper_texts = []
        # 为分析内容设定一个安全的最大token数，为其他提示词部分留出余量
        MAX_CONTENT_TOKENS = 7500 
        tokenizer = PromptManager._get_tokenizer()

        for paper in papers:
            content_key = "Full Text"
            content_value = paper.get('full_text')
            
            if not content_value:
                content_key = "Abstract"
                content_value = paper.get('abstract', 'N/A')
            
            # 使用tokenizer进行精确截断
            if tokenizer:
                tokens = tokenizer.encode(content_value)
                if len(tokens) > MAX_CONTENT_TOKENS:
                    truncated_tokens = tokens[:MAX_CONTENT_TOKENS]
                    content_value = tokenizer.decode(truncated_tokens, errors='ignore') + "\n... (内容已截断)"
            else:
                # 如果tokenizer加载失败，回退到基于字符的截断
                if len(content_value) > 25000: # 粗略估算
                    content_value = content_value[:25000] + "\n... (内容已截断)"

            paper_texts.append(
f"""---
**Paper ID**: {paper['paper_id']}
**Title**: {paper['title']}
**{content_key}**:
{content_value.replace('{', '{{').replace('}', '}}')}
---"""
            )
        return "请对以下每篇论文提供完整的六维度分析，使用分隔符清晰格式化。如果提供了全文，必须基于全文进行分析。\n" + "\n".join(paper_texts)

    @staticmethod
    def get_stage1_ranking_system_prompt() -> str:
        """获取第一阶段强制排名系统提示词"""
        return """你是AI论文评审专家。任务是对一批论文进行相对质量排名。

**严格规则**：
1. **相对排名**：必须相互比较，确定相对新颖性、重要性和潜在影响
2. **强制分布评分**：必须按批次内排名分配分数，遵循以下分布：
   - **前10%**：4.5-5.0分（突破性工作）
   - **接下来20%**：3.5-4.4分（重要且有趣）
   - **中间40%**：2.5-3.4分（扎实的渐进贡献）
   - **后30%**：1.0-2.4分（次要/影响有限/有缺陷）
3. **JSON输出**：必须返回JSON列表，每个元素包含paper_id、score和justification。不要包含JSON之外的任何文本。

示例（10篇论文）：
[
  {"paper_id": "2401.0001", "score": 4.8, "justification": "突破性方法解决长期问题"},
  {"paper_id": "2401.0005", "score": 4.1, "justification": "显著超越SOTA，结果强劲"},
  {"paper_id": "2401.0008", "score": 3.9, "justification": "现有方法的新颖应用"},
  {"paper_id": "2401.0002", "score": 3.2, "justification": "扎实的渐进工作，实验良好"},
  {"paper_id": "2401.0004", "score": 3.1, "justification": "可以接受的贡献，但缺乏新颖性"},
  {"paper_id": "2401.0007", "score": 2.8, "justification": "渐进工作，验证有限"},
  {"paper_id": "2401.0009", "score": 2.5, "justification": "标准方法，结果可预见"},
  {"paper_id": "2401.0003", "score": 2.1, "justification": "次要贡献，局限性较多"},
  {"paper_id": "2401.0006", "score": 1.8, "justification": "方法有缺陷，结果不可信"},
  {"paper_id": "2401.0010", "score": 1.5, "justification": "新颖性极其有限，证据薄弱"}
]
"""

    @staticmethod
    def format_stage1_ranking_prompt(papers: list[Dict[str, Any]]) -> str:
        """格式化第一阶段排名的用户提示词"""
        paper_texts = []
        for paper in papers:
            # 使用 json.dumps 来安全地处理摘要和标题中的特殊字符（如引号）
            abstract = json.dumps(paper.get('abstract', '').replace("\n", " "))
            title = json.dumps(paper.get('title', ''))
            paper_texts.append(
f"""    {{
        "paper_id": "{paper.get('paper_id', 'N/A')}",
        "title": {title},
        "abstract": {abstract}
    }}"""
            )
        return f"请根据系统提示中的规则对以下论文进行排名。论文列表：\n[\n{',\\n'.join(paper_texts)}\n]"

    @staticmethod
    def format_analysis_for_html(analysis_text: str) -> str:
        """将AI分析结果格式化为HTML"""
        if not isinstance(analysis_text, str) or not analysis_text.strip():
            return "<p>AI analysis not available.</p>"

        sections = {
            "⭐ 质量评估": "star",
            "🎯 核心贡献": "bullseye",
            "🔧 技术方法": "wrench",
            "🧪 实验验证": "beaker",
            "💡 影响意义": "lightbulb",
            "🔮 局限展望": "crystal-ball"
        }
        
        html_content = ""
        
        # 使用正则表达式按维度分割，同时保留分隔符
        parts = re.split(r'(⭐|🎯|🔧|🧪|💡|🔮)', analysis_text)
        
        # parts[0]是第一个分隔符之前的内容（通常为空），之后是 (分隔符, 内容) 对
        content_parts = [parts[i] + parts[i+1] for i in range(1, len(parts), 2)]

        for part in content_parts:
            for title, icon in sections.items():
                if part.strip().startswith(title):
                    # 移除标题本身和前后的空格
                    content = part.replace(title, "", 1).strip()
                    # 格式化内容
                    formatted_content = PromptManager._format_text_content(content)
                    html_content += f"""
                    <div class="analysis-dimension">
                        <div class="dimension-title">
                            <i class="fas fa-{icon}"></i>
                            <h4>{title.split(' ')[1]}</h4>
                        </div>
                        <p>{formatted_content}</p>
                    </div>
                    """
                    break # 匹配到就处理下一个part
        
        if not html_content:
            # 如果分割失败，提供原始文本作为后备
            return f"<p>{analysis_text.replace('<', '&lt;').replace('>', '&gt;')}</p>"

        return f'<div class="ai-analysis-container">{html_content}</div>'

    @staticmethod
    def _format_text_content(text: str) -> str:
        """格式化文本内容，处理加粗和换行"""
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        # 转换 **加粗** 为 <strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        # 转换 *斜体* 为 <em>
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        # 转换换行符
        text = text.replace('\n', '<br>')
        return text 