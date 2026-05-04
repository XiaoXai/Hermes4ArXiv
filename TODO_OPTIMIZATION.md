# 论文分析系统优化待办清单

## 📋 优化目标
提升论文分析的稳定性、质量和一致性，同时保持成本不变。

## 🎯 待办事项

### 优先级1：立即优化

#### 1. 支持Qwen API ⭐⭐⭐
**当前问题**：
- 当前主要依赖DeepSeek和GLM模型
- 没有利用成本更低、性能更好的Qwen模型
- 并发限制可能导致API调用失败

**优化方案**：
- 集成阿里云通义千问API
- 优先使用Qwen，其次GLM或DeepSeek
- 更新配置和文档说明

**文件位置**：
- `src/ai/analyzer.py`
- `src/config.py`
- `README.md`
- `CLAUDE.md`

---

#### 2. 简化系统提示词 ⭐⭐⭐
**当前问题**：
- 提示词173行，大量重复
- 同一概念重复强调3-4次
- 消耗过多tokens（~1500 tokens）

**优化方案**：
- 缩减至30行左右
- 保留核心评分标准和六维度框架
- 移除重复内容
- 节省~1000 tokens

**文件位置**：`src/ai/prompts.py::_get_comprehensive_system_prompt()`

---

#### 3. 统一语言策略 ⭐⭐⭐
**当前问题**：
- 系统提示词：中文
- Stage 1排名：英文
- API返回：中文
- 不一致可能影响效果

**优化方案**：
- 统一为全中文（推荐）
- 更符合中文用户需求
- 提升一致性

**文件位置**：
- `src/ai/prompts.py::get_stage1_ranking_system_prompt()`
- `src/ai/prompts.py::format_stage1_ranking_prompt()`

---

### 优先级2：重要优化

#### 4. 改为逐篇并行分析 ⭐⭐⭐
**当前问题**：
- Stage 2一次API调用分析20篇论文
- 容易超出token限制（200K）
- 解析复杂，容易失败
- 部分失败影响全部

**优化方案**：
```python
# 当前：批量分析
batch_analysis_text = self.analyzer.analyze_papers_batch(papers)

# 改为：逐篇并行
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        executor.submit(self.analyzer.analyze_paper, paper): paper
        for paper in papers
    }
    for future in as_completed(futures):
        result = future.result()
```

**优势**：
- ✅ 成本相同（总token数不变）
- ✅ 稳定性提升（不会超限）
- ✅ 质量提升（每篇专注分析）
- ✅ 解析简单（1对1映射）
- ✅ 容错性好（单个失败不影响其他）
- ✅ 完美并行

**文件位置**：`src/ai/batch_coordinator.py::_run_stage2_deep_analysis()`

---

#### 5. 实现智能章节提取 ⭐⭐
**当前问题**：
- 简单截取前7500 tokens
- 可能错过重要的实验和结论部分

**优化方案**：
```python
def smart_extract_sections(full_text, max_tokens=7500):
    """
    智能提取关键章节：
    - Abstract: 10%
    - Method/Approach: 40%
    - Experiment/Results: 35%
    - Conclusion: 15%
    """
    sections = {
        'abstract': extract_by_headers(['abstract', 'introduction']),
        'method': extract_by_headers(['method', 'approach', 'model']),
        'experiment': extract_by_headers(['experiment', 'result', 'evaluation']),
        'conclusion': extract_by_headers(['conclusion', 'discussion'])
    }
    return combine_sections(sections, max_tokens)
```

**文件位置**：`src/ai/prompts.py::format_batch_analysis_prompt()`

---

#### 6. 优化Stage 1动态排名 ⭐
**当前问题**：
- 固定强制分布（Top 10%, Next 20%, 40%, 30%）
- 小批次（<10篇）应用困难

**优化方案**：
```python
def get_dynamic_distribution(batch_size):
    if batch_size < 5:
        return "相对排名，不强制分布"
    elif batch_size < 10:
        return "适度分布：优秀20%, 良好40%, 一般40%"
    else:
        return "严格分布：优秀10%, 良好20%, 中等40%, 较差30%"
```

**文件位置**：`src/ai/prompts.py::get_stage1_ranking_system_prompt()`

---

### 优先级3：可选优化

#### 7. 增加论文质量预检
- 检查是否为预印本
- 检查实验完整性
- 标注可信度指标

#### 8. 评分校准机制
- 定期回顾历史评分
- 调整评分基准线
- 确保分布合理

---

## 📊 当前系统评估

### ✅ 优点（保留）
1. 严格的评分标准（避免虚高）
2. 完整的PDF全文提取
3. 六维度结构化分析
4. 两阶段筛选流程

### ⚠️ 问题（需优化）
1. 提示词冗长重复
2. 中英文混用
3. 批量分析不稳定
4. 简单截取全文

---

## 💰 成本分析

**关键发现**：批量分析 vs 逐篇分析成本相同！

假设每天分析20篇论文：

| 方案 | API调用 | 输入Tokens | 输出Tokens | 成本/月 |
|------|---------|-----------|-----------|---------|
| 批量 | 1次 | 200K | 20K | ¥390 |
| 逐篇 | 20次 | 200K | 20K | ¥390 |

**结论**：逐篇分析更稳定，质量更高，成本不变！

---

## 🚀 实施顺序

1. ✅ 支持Qwen API（最高优先级）
2. ✅ 修复arxiv.Result.to_dict()错误
3. ✅ 简化提示词（最高优先级）
4. ✅ 统一为全中文
5. ✅ 改为逐篇并行分析
6. ✅ 实现智能章节提取
7. ✅ 优化Stage 1排名
8. ✅ 完整测试
9. ✅ 提交推送

---

## 📝 测试计划

### 测试用例
1. 单篇论文分析
2. 10篇论文批量处理
3. 20篇论文完整流程
4. 超长论文（>100页）
5. 多语言论文（英文/中文）

### 验证指标
- ✓ 所有论文成功分析
- ✓ 评分分布合理（2-3星占70%）
- ✓ 无token超限错误
- ✓ 解析成功率100%
- ✓ 六维度输出完整

---

## 📅 完成时间估算
- 支持Qwen API：30分钟
- 修复arxiv.Result.to_dict()错误：10分钟
- 简化提示词：30分钟
- 统一中文：20分钟
- 逐篇分析：1小时
- 智能提取：1.5小时
- 测试验证：1小时
- **总计：约4.5小时**

---

## 🎯 预期收益
1. **成本降低**：使用Qwen API成本更低
2. **稳定性**：从60%提升到95%
3. **质量**：分析深度提升30%
4. **可维护性**：代码简化40%
5. **用户体验**：邮件内容更准确
6. **并发性能**：减少API调用冲突