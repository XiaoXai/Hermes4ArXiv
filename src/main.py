#!/usr/bin/env python3
"""
ArXiv论文追踪与分析器
使用模块化架构，支持更好的扩展性和维护性
"""

import sys
import traceback
from pathlib import Path

from src.data.arxiv_client import ArxivClient
from src.config import Config
from src.output.email_sender import EmailSender
from src.output.formatter import OutputFormatter
from src.ai.analyzer import DeepSeekAnalyzer
from src.ai.batch_coordinator import BatchCoordinator
from src.utils.logger import logger


def arxiv_result_to_dict(paper) -> dict:
    """
    Convert arxiv.Result object to dictionary format

    Args:
        paper: arxiv.Result object

    Returns:
        Dictionary with paper information
    """
    # Get author names safely
    author_names = []
    if hasattr(paper, 'authors') and paper.authors:
        try:
            author_names = [author.name for author in paper.authors]
        except AttributeError:
            logger.warning(f"Abnormal author object structure for paper: {paper.title}")

    # Get published date safely
    published_date = None
    if hasattr(paper, 'published') and paper.published:
        published_date = paper.published

    # Get PDF URL safely
    pdf_url = None
    if hasattr(paper, 'pdf_url'):
        pdf_url = paper.pdf_url
    else:
        # Derive PDF URL from entry_id
        pdf_url = paper.entry_id.replace('/abs/', '/pdf/') + '.pdf'

    return {
        'title': paper.title,
        'authors': author_names,
        'categories': paper.categories,
        'published': published_date,
        'entry_id': paper.entry_id,
        'summary': paper.summary,
        'pdf_url': pdf_url,
        'paper_id': paper.get_short_id()
    }


class ArxivPaperTracker:
    """ArXiv论文追踪器主类"""

    def __init__(self):
        """初始化追踪器"""
        self.config = Config()
        self.arxiv_client = None
        self.ai_analyzer = None
        self.batch_coordinator = None
        self.output_formatter = None
        self.email_sender = None

        if not self.config.validate():
            raise ValueError("配置验证失败，请检查环境变量设置")

        self.config.create_directories()
        self._initialize_components()

    def _initialize_components(self):
        """初始化各个组件"""
        try:
            self.ai_analyzer = DeepSeekAnalyzer(self.config)
            
            self.arxiv_client = ArxivClient(
                categories=self.config.CATEGORIES,
                max_papers=self.config.MAX_PAPERS,
                search_days=self.config.SEARCH_DAYS
            )
            
            self.batch_coordinator = BatchCoordinator(self.config, self.ai_analyzer, self.arxiv_client)

            self.output_formatter = OutputFormatter(
                self.config.TEMPLATES_DIR, 
                self.config.GITHUB_REPO_URL
            )

            self.email_sender = EmailSender.create_from_config(self.config)

            logger.info("所有组件初始化完成")

        except Exception as e:
            logger.error(f"组件初始化失败: {e}", exc_info=True)
            raise

    def run(self):
        """运行论文追踪和分析流程"""
        try:
            logger.info("="*50)
            logger.info("开始ArXiv论文追踪和分析")

            # 1. 从ArXiv获取新论文
            logger.info("Fetching new papers from ArXiv...")
            new_papers = self.arxiv_client.get_recent_papers()
            if not new_papers:
                logger.info("没有找到新的论文，流程结束。")
                return
            
            logger.info(f"成功从ArXiv获取 {len(new_papers)} 篇论文。")

            # 将arxiv.Result对象和其字典形式一起准备，以供后续使用
            papers_for_analysis = [(p, arxiv_result_to_dict(p)) for p in new_papers]

            # 2. 使用BatchCoordinator进行分析
            # BatchCoordinator现在接收(arxiv.Result, dict)的元组列表
            analyzed_papers_dicts = self.batch_coordinator.run_batch_analysis(papers_for_analysis)

            if not analyzed_papers_dicts:
                logger.warning("分析流程未产生任何成功分析的论文。")
                return
            
            logger.info(f"成功分析 {len(analyzed_papers_dicts)} 篇论文。")
            
            # 将分析结果与原始ArXiv数据重新组合以进行格式化
            final_results_for_formatting = []
            for paper_data in analyzed_papers_dicts:
                # 从原始论文列表中找到匹配的arxiv.Result对象
                original_paper = next((p for p in new_papers if p.get_short_id() == paper_data.get('paper_id')), None)
                if original_paper:
                    final_results_for_formatting.append((original_paper, paper_data))

            # 3. 生成输出
            self._generate_outputs(final_results_for_formatting)

            # 4. 发送邮件
            self._send_email_report(final_results_for_formatting)

            logger.info("ArXiv论文追踪和分析流程成功完成。")
            logger.info("="*50)

        except Exception as e:
            error_msg = f"运行过程中发生严重错误: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)

            if self.email_sender and self.config.EMAIL_TO:
                self.email_sender.send_error_notification(
                    self.config.EMAIL_TO, error_msg
                )
            raise

    def _generate_outputs(self, papers_analyses):
        """生成各种格式的输出"""
        if not papers_analyses:
            logger.info("没有已分析的论文可供生成报告。")
            return
        try:
            logger.info("正在生成输出报告...")
            # Format and save markdown report to conclusion.md
            markdown_content = self.output_formatter.format_markdown(papers_analyses)
            with open(self.config.CONCLUSION_FILE, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Generate and save HTML report
            html_content = self.output_formatter.format_html_email(papers_analyses)
            with open(self.config.HTML_REPORT_FILE, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            logger.info(f"报告已生成: {self.config.CONCLUSION_FILE} 和 {self.config.HTML_REPORT_FILE}")

        except Exception as e:
            logger.error(f"生成输出失败: {e}", exc_info=True)
            raise

    def _send_email_report(self, papers_analyses):
        """发送邮件报告"""
        if not self.email_sender or not self.config.EMAIL_TO:
            logger.info("邮件配置不完整，跳过发送邮件")
            return
        
        if not papers_analyses:
            logger.info("没有成功分析的论文，不发送报告。")
            return

        try:
            logger.info("正在准备并发送邮件报告...")
            html_content = self.output_formatter.format_html_email(papers_analyses)
            subject = self.output_formatter.get_email_subject()
            
            self.email_sender.send_email(
                to_emails=self.config.EMAIL_TO,
                subject=subject,
                content=html_content
            )
            logger.info(f"邮件报告已成功发送至 {', '.join(self.config.EMAIL_TO)}")
        except Exception as e:
            logger.error(f"发送邮件报告失败: {e}", exc_info=True)
            raise

def main():
    """主函数入口"""
    try:
        tracker = ArxivPaperTracker()
        tracker.run()
    except Exception as e:
        logger.critical(f"应用启动或运行过程中发生致命错误: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()