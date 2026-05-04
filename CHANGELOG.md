# 更新日志

## [2025-01-20] 重大更新

### 🔧 修复的问题

1. **ModuleNotFoundError: No module named 'src.db'**
   - 清理了Python缓存文件（`__pycache__`和`.pyc`）
   - 移除了不存在的`src.db`模块引用

2. **API上下文限制问题**
   - 添加了智谱GLM-4支持，提供更大的上下文窗口
   - 智谱GLM更适合阅读和分析完整论文内容
   - 保留了DeepSeek作为备选方案

3. **邮件模板优化**
   - 简化了邮件HTML模板，回归简洁美观的设计
   - 去除了过多的装饰元素
   - 优化了移动端显示效果
   - 提升了邮件加载速度

### ✨ 新增功能

- **多AI模型支持**：现在支持智谱GLM-4.6和DeepSeek两种AI模型
  - 优先使用智谱GLM-4.6（如果配置了`GLM_API_KEY`）
    - 200K tokens 上下文窗口
    - 128K tokens 最大输出
  - 自动降级到DeepSeek（如果只配置了`DEEPSEEK_API_KEY`）
  - 两种模型可以灵活切换，无需修改代码

- **智能API适配**：根据不同的AI提供商自动调整API调用参数
  - 智谱GLM：使用官方SDK `zhipuai`
  - DeepSeek：使用OpenAI兼容接口

### 📝 配置变更

**新增环境变量：**
```bash
GLM_API_KEY=your-glm-api-key        # 智谱GLM API密钥（推荐）
GLM_MODEL=glm-4-plus                # 智谱GLM模型名称（可选）
```

**现有配置保持不变：**
```bash
DEEPSEEK_API_KEY=sk-your-key        # DeepSeek API密钥（备选）
DEEPSEEK_MODEL=deepseek-chat        # DeepSeek模型名称（可选）
```

### 📦 依赖更新

添加了新依赖：
```toml
zhipuai>=2.0.0  # 智谱GLM官方SDK
```

### 🚀 升级指南

1. **更新依赖**（如果本地运行）：
   ```bash
   uv sync
   ```

2. **配置智谱GLM API**（推荐）：
   - 访问 https://open.bigmodel.cn/
   - 注册并获取API密钥
   - 在GitHub Secrets中添加`GLM_API_KEY`

3. **或继续使用DeepSeek**：
   - 保持现有的`DEEPSEEK_API_KEY`配置即可
   - 无需任何修改

### 🎯 使用建议

- **推荐使用智谱GLM-4.6**：
  - ✅ 超大上下文窗口（200K tokens输入）
  - ✅ 大输出能力（128K tokens输出）
  - ✅ 更适合阅读和分析完整论文PDF
  - ✅ 更准确的深度论文分析

- **DeepSeek作为备选**：
  - ✅ 仍然是一个可靠的选择
  - ✅ 成本可能更低
  - ✅ 响应速度可能更快
  - ⚠️  上下文窗口相对较小

### 📋 待办事项

- [ ] 添加更多AI模型支持（如OpenAI GPT-4）
- [ ] 优化论文PDF文本提取性能
- [ ] 添加论文分析缓存机制
- [ ] 支持自定义邮件模板

### 🐛 已知问题

- 无

---

## 历史版本

查看 git log 获取完整的历史记录。
