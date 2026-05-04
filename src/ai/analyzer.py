#!/usr/bin/env python3
"""
AI 分析器模块
支持多种AI模型：智谱GLM、DeepSeek等
"""

import logging
import time
import json
from typing import Dict, Any, List

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Config
from .prompts import PromptManager

logger = logging.getLogger(__name__)


class DeepSeekAnalyzer:
    """
    AI论文分析器，支持多种AI模型。
    支持完整的两阶段分析流程。
    """

    def __init__(self, config: Config):
        """
        初始化分析器，从配置中加载设置。
        """
        self.config = config
        self.timeout = config.API_TIMEOUT

        # 自动检测使用哪个API
        if config.QWEN_API_KEY:
            # 优先使用Qwen
            logger.info("使用Qwen模型进行分析")
            self.model = config.QWEN_MODEL or "qwen3-max"
            self.provider = "qwen"
            self.client = openai.OpenAI(
                api_key=config.QWEN_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        elif config.GLM_API_KEY:
            # 使用智谱GLM（次优选择）
            from zhipuai import ZhipuAI
            logger.info("使用智谱GLM模型进行分析")
            self.model = config.GLM_MODEL or "glm-4.6"
            self.provider = "glm"
            self.client = ZhipuAI(api_key=config.GLM_API_KEY)
        elif config.DEEPSEEK_API_KEY:
            # 使用DeepSeek
            logger.info("使用DeepSeek模型进行分析")
            self.model = config.DEEPSEEK_MODEL or "deepseek-chat"
            self.provider = "deepseek"
            self.client = openai.OpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
        else:
            raise ValueError("未找到有效的API密钥。请配置 QWEN_API_KEY、GLM_API_KEY 或 DEEPSEEK_API_KEY")

    def _create_completion(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, **kwargs) -> str:
        """
        统一的API调用接口，处理不同provider的差异
        """
        try:
            if self.provider == "glm":
                # 智谱GLM不支持response_format和timeout参数
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            else:
                # Qwen和DeepSeek都支持完整的OpenAI参数
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"API调用失败: {e}", exc_info=True)
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def rank_papers_in_batch(self, papers: list[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对一小批论文进行强制排名和评分 (Stage 1).
        返回一个包含评分结果的列表。
        """
        logger.info(f"Executing Stage 1: Ranking a batch of {len(papers)} papers using {self.provider}.")
        if not papers:
            return []

        response_text = ""
        try:
            system_prompt = PromptManager.get_stage1_ranking_system_prompt()
            user_prompt = PromptManager.format_stage1_ranking_prompt(papers)

            # 根据provider选择合适的参数
            if self.provider == "glm":
                response_text = self._create_completion(
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    max_tokens=2048,
                    temperature=0.2
                )
            else:
                response_text = self._create_completion(
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    max_tokens=2048,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    timeout=self.timeout
                )
            logger.debug(f"Raw Stage 1 ranking response from AI: {response_text}")
            
            parsed_json = json.loads(response_text)
            
            if isinstance(parsed_json, dict):
                ranking_list = next((v for v in parsed_json.values() if isinstance(v, list)), None)
                if ranking_list is None:
                    logger.error("AI returned a JSON object for ranking, but no list was found inside.")
                    return []
            elif isinstance(parsed_json, list):
                ranking_list = parsed_json
            else:
                logger.error(f"AI ranking response was not a JSON list or a dict containing a list. Type: {type(parsed_json)}")
                return []

            if not all('paper_id' in item and 'score' in item for item in ranking_list):
                logger.error("AI ranking response list has malformed items.")
                return []
                
            return ranking_list

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from AI ranking response: {e}\nProblematic text: {response_text}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred during paper ranking: {e}", exc_info=True)
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_papers_batch(self, papers: list[Dict[str, Any]]) -> str:
        """
        对一批论文进行深入的批量分析 (Stage 2).
        返回一个包含所有分析的长字符串。
        """
        logger.info(f"Executing Stage 2: Performing deep analysis on a batch of {len(papers)} papers using {self.provider}.")
        if not papers:
            return ""

        system_prompt = PromptManager.get_system_prompt()
        user_prompt = PromptManager.format_batch_analysis_prompt(papers)

        if self.provider == "glm":
            analysis_text = self._create_completion(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=8000,
                temperature=0.5
            )
        else:
            analysis_text = self._create_completion(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=8000,
                temperature=0.5,
                stream=False,
                timeout=self.timeout * 2
            )
        logger.info(f"Successfully completed deep analysis for {len(papers)} papers.")
        return analysis_text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_paper(self, paper: Dict[str, Any]) -> str:
        """
        对单篇论文进行深入分析 (用于后备或单次运行).
        返回包含分析结果的字符串。
        """
        from .prompts import PromptManager  # 局部导入以避免作用域问题
        
        logger.info(f"Performing single paper analysis for: {paper.get('title', 'N/A')} using {self.provider}.")
        system_prompt = PromptManager.get_system_prompt()

        # 检查是否提供了全文，如果是，则优先使用全文进行分析
        content_to_analyze = paper.get('full_text') or paper.get('abstract', '摘要不可用')
        
        # 为内容设定一个安全的最大token数，为其他提示词部分留出余量
        # 根据不同模型的上下文窗口适当调整
        MAX_CONTENT_TOKENS = 20000  # 增加到20000 tokens，为系统提示词和输出留出充足空间
        tokenizer = PromptManager._get_tokenizer()

        # 使用tokenizer进行精确截断
        if tokenizer and content_to_analyze:
            tokens = tokenizer.encode(content_to_analyze)
            if len(tokens) > MAX_CONTENT_TOKENS:
                truncated_tokens = tokens[:MAX_CONTENT_TOKENS]
                content_to_analyze = tokenizer.decode(truncated_tokens, errors='ignore') + "\n... (内容已截断)"
        elif content_to_analyze and len(content_to_analyze) > 80000:  # 如果tokenizer加载失败，回退到基于字符的截断
            content_to_analyze = content_to_analyze[:80000] + "\n... (内容已截断)"

        # 构建用户提示词，优先使用全文内容
        user_prompt = f"""请分析以下ArXiv论文：
📄 **论文标题**：{paper.get('title', '未知标题')}
👥 **作者信息**：{paper.get('authors', '未知作者')}
🏷️ **研究领域**：{paper.get('categories', '未知领域')}
📅 **发布时间**：{paper.get('published_date', '未知日期')}
📝 **论文摘要**：{paper.get('abstract', '摘要不可用')}
🔗 **论文链接**：https://arxiv.org/abs/{paper.get('paper_id', '')}
---
📄 **论文内容**：{content_to_analyze}
---
请基于以上信息，按照系统提示的结构进行深度分析。"""

        if self.provider == "glm":
            # 智谱GLM不支持response_format参数
            return self._create_completion(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=2000,
                temperature=0.7
            )
        else:
            # Qwen和DeepSeek支持response_format参数，以获得更结构化的输出
            return self._create_completion(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=2000,
                temperature=0.7,
                response_format={"type": "text"},  # 使用text格式以保持现有格式，如需严格JSON可改为{"type": "json_object"}
                timeout=self.timeout
            ) 