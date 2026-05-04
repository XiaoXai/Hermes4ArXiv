#!/usr/bin/env python3
"""
批量分析协调器
管理论文批次处理和两阶段分析流程。
"""

import logging
import re
from collections import defaultdict
from typing import Dict, Any, List, Tuple
import concurrent.futures

import arxiv
from .analyzer import DeepSeekAnalyzer
from ..config import Config
from .prompts import PromptManager
from ..data.arxiv_client import ArxivClient

logger = logging.getLogger(__name__)


class BatchCoordinator:
    """批量分析协调器，负责编排整个分析流程。"""

    def __init__(self, config: Config, analyzer: DeepSeekAnalyzer, arxiv_client: ArxivClient):
        self.config = config
        self.analyzer = analyzer
        self.arxiv_client = arxiv_client

    def run_batch_analysis(self, papers_to_process: List[Tuple[arxiv.Result, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        运行批量分析。如果启用了两阶段分析，则执行新流程，否则执行旧的直接分析流程。
        """
        use_stage_analysis = self.config.STAGE_ANALYSIS.get('ENABLED', False)

        if not use_stage_analysis:
            logger.info("Two-stage analysis is disabled. Running legacy direct batch analysis.")
            return self._run_legacy_batch_analysis(papers_to_process)

        logger.info("Starting two-stage analysis pipeline.")

        # Stage 1: Sliding Window Ranking
        paper_dictionaries = [p_dict for _, p_dict in papers_to_process]
        papers_with_scores = self._run_stage1_ranking(paper_dictionaries)
        if not papers_with_scores:
            logger.warning("Stage 1 ranking resulted in no papers. Aborting.")
            return []

        # Stage 2: Filtering and Deep Analysis
        final_results = self._run_stage2_deep_analysis(papers_with_scores, papers_to_process)
        
        logger.info("Two-stage analysis pipeline finished.")
        return final_results

    def _run_stage1_ranking(self, all_paper_dicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行第一阶段：滑动窗口排名。返回带有聚合分数的论文列表。
        """
        stage1_config = self.config.STAGE_ANALYSIS.get('STAGE1', {})
        window_size = stage1_config.get('WINDOW_SIZE', 10)
        step_size = stage1_config.get('STEP_SIZE', 5)
        
        if step_size <= 0:
            logger.error("Sliding window step_size must be positive. Defaulting to 1.")
            step_size = 1

        logger.info(f"Stage 1: Creating sliding window batches (size: {window_size}, step: {step_size}).")
        
        paper_chunks = []
        for i in range(0, len(all_paper_dicts), step_size):
            chunk = all_paper_dicts[i : i + window_size]
            if chunk:
                # 避免最后产生一个过小的批次
                if len(paper_chunks) > 0 and len(chunk) < window_size / 2:
                    paper_chunks[-1].extend(chunk)
                    break
                paper_chunks.append(chunk)

        stage1_scores = defaultdict(list)
        
        # 并行执行所有批次的排名
        max_workers = self.config.MAX_WORKERS if self.config.MAX_WORKERS > 0 else None
        logger.info(f"Ranking {len(paper_chunks)} chunks in parallel using up to {max_workers or 'default'} workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk_index = {
                executor.submit(self.analyzer.rank_papers_in_batch, chunk): i
                for i, chunk in enumerate(paper_chunks)
            }

            for future in concurrent.futures.as_completed(future_to_chunk_index):
                chunk_index = future_to_chunk_index[future]
                try:
                    ranking_results = future.result()
                    for result in ranking_results:
                        paper_id = result.get('paper_id')
                        score = result.get('score')
                        if paper_id and isinstance(score, (int, float)):
                            stage1_scores[paper_id].append(float(score))
                except Exception as e:
                    logger.error(f"Error ranking chunk {chunk_index + 1}: {e}", exc_info=True)

        final_scores = {paper_id: max(scores) for paper_id, scores in stage1_scores.items() if scores}
        
        # 将分数附加回原始字典列表
        for paper_dict in all_paper_dicts:
            paper_id = paper_dict.get('paper_id')
            score = final_scores.get(paper_id)
            paper_dict['stage1_score'] = score if score is not None else 0.0

        all_paper_dicts.sort(key=lambda p: p.get('stage1_score', 0.0), reverse=True)
        
        logger.info(f"Stage 1: Completed ranking for {len(final_scores)} papers.")
        return all_paper_dicts

    def _run_stage2_deep_analysis(self, papers_with_scores: List[Dict[str, Any]], all_papers_tuples: List[Tuple[arxiv.Result, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        执行第二阶段：筛选、并行提取全文，并对顶尖论文进行深度分析。
        """
        stage1_config = self.config.STAGE_ANALYSIS.get('STAGE1', {})
        stage2_config = self.config.STAGE_ANALYSIS.get('STAGE2', {})
        promotion_threshold = stage1_config.get('PROMOTION_SCORE_THRESHOLD', 3.5)
        max_to_analyze = stage2_config.get('MAX_PAPERS_TO_ANALYZE', 20)

        promoted_paper_ids = {p['paper_id'] for p in papers_with_scores if p.get('stage1_score', 0.0) >= promotion_threshold}
        
        # 从原始元组列表中筛选出优胜者
        all_papers_map = {p_dict['paper_id']: (p_res, p_dict) for p_res, p_dict in all_papers_tuples}
        promoted_papers_tuples = [all_papers_map[pid] for pid in promoted_paper_ids if pid in all_papers_map]
        
        # 按分数排序并截取
        promoted_papers_tuples.sort(key=lambda x: x[1]['stage1_score'], reverse=True)
        top_papers_to_analyze_tuples = promoted_papers_tuples[:max_to_analyze]

        logger.info(f"Stage 2: {len(top_papers_to_analyze_tuples)} papers promoted for deep analysis (threshold: >={promotion_threshold}, max: {max_to_analyze}).")

        if not top_papers_to_analyze_tuples:
            logger.info("No papers met the threshold for deep analysis.")
            return []

        # 并行提取全文并进行分析（逐篇并行）
        max_workers = self.config.MAX_WORKERS if self.config.MAX_WORKERS > 0 else None
        logger.info(f"Extracting full text and analyzing {len(top_papers_to_analyze_tuples)} papers in parallel using up to {max_workers or 'default'} workers...")

        analyzed_papers_with_details = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 为每篇论文提交一个完整的任务（提取全文 + 分析）
            future_to_paper = {
                executor.submit(self._analyze_single_paper, arxiv_res, paper_dict): paper_dict
                for arxiv_res, paper_dict in top_papers_to_analyze_tuples
            }

            for future in concurrent.futures.as_completed(future_to_paper):
                paper_dict = future_to_paper[future]
                try:
                    analyzed_paper = future.result()
                    if analyzed_paper:
                        analyzed_papers_with_details.append(analyzed_paper)
                        logger.info(f"Successfully analyzed paper {analyzed_paper['paper_id']}")
                except Exception as e:
                    logger.error(f"Failed to analyze paper {paper_dict['paper_id']}: {e}", exc_info=True)

        logger.info(f"Stage 2 completed: {len(analyzed_papers_with_details)}/{len(top_papers_to_analyze_tuples)} papers successfully analyzed")
        return analyzed_papers_with_details

    def _analyze_single_paper(self, arxiv_res: arxiv.Result, paper_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单篇论文（提取全文 + AI分析）
        这个方法在 ThreadPoolExecutor 中并行运行
        """
        paper_id = paper_dict.get('paper_id', 'unknown')

        # 步骤1：提取全文
        try:
            full_text = self.arxiv_client.get_full_text(arxiv_res, self.config.PAPERS_DIR)
            if full_text:
                paper_dict['full_text'] = full_text
                logger.debug(f"Extracted full text for {paper_id}")
            else:
                logger.warning(f"Could not extract full text for {paper_id}, using abstract only")
        except Exception as e:
            logger.error(f"Error extracting full text for {paper_id}: {e}", exc_info=True)

        # 步骤2：AI 分析
        try:
            analysis_text = self.analyzer.analyze_paper(paper_dict)

            # 格式化为 HTML
            from .prompts import PromptManager
            html_analysis = PromptManager.format_analysis_for_html(analysis_text)

            # 附加分析结果
            paper_dict['analysis'] = analysis_text
            paper_dict['html_analysis'] = html_analysis

            return paper_dict

        except Exception as e:
            logger.error(f"Error analyzing paper {paper_id}: {e}", exc_info=True)
            return None

    def _run_legacy_batch_analysis(self, papers_to_process: List[Tuple[arxiv.Result, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        原始的、直接的批量分析方法。
        """
        batch_size = self.config.BATCH_SIZE
        paper_chunks = [papers_to_process[i:i + batch_size] for i in range(0, len(papers_to_process), batch_size)]
        
        all_analyzed_papers = []
        for chunk in paper_chunks:
            # 准备仅包含字典的列表以供分析
            chunk_dicts = [p_dict for _, p_dict in chunk]
            try:
                logger.info(f"Analyzing a legacy batch of {len(chunk_dicts)} papers.")
                analysis_text = self.analyzer.analyze_papers_batch(chunk_dicts)
                parsed_results = self._parse_batch_analysis(analysis_text, chunk_dicts)
                
                for _, paper_dict in chunk:
                    paper_id = paper_dict['paper_id']
                    if paper_id in parsed_results:
                        # 将分析结果直接附加到论文数据字典中
                        paper_dict.update(parsed_results[paper_id])
                        all_analyzed_papers.append(paper_dict)
            except Exception as e:
                logger.error(f"Error processing legacy batch: {e}", exc_info=True)
        return all_analyzed_papers

    def _parse_batch_analysis(self, batch_text: str, papers_in_batch: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """
        解析批量分析文本，返回一个包含每个论文分析结果的字典。
        """
        paper_ids = [p['paper_id'] for p in papers_in_batch]
        results = {}
        
        if not batch_text or not paper_ids:
            return results

        split_pattern = r'Paper ID\s*:\s*(' + '|'.join(re.escape(pid) for pid in paper_ids) + ')'
        parts = re.split(split_pattern, batch_text)
        
        if len(parts) < 3:
            logger.warning(f"Could not split batch analysis text. Text: '{batch_text[:200]}...'")
            return {}

        for i in range(1, len(parts), 2):
            paper_id = parts[i]
            content_with_header = parts[i+1]
            # The actual analysis content starts after the header part (Title, Abstract, etc.)
            # A simple way is to find the end of the abstract marker '---'
            content_parts = re.split(r'---\s*\n', content_with_header, maxsplit=1)
            raw_content = content_parts[-1].strip()
            
            html_analysis = PromptManager.format_analysis_for_html(raw_content)
            results[paper_id] = {'raw': raw_content, 'html': html_analysis}
            logger.info(f"Successfully parsed analysis for paper {paper_id}.")

        return results 