# 📚 高级配置指南

本文档提供详细的配置说明和自定义选项，适合需要个性化设置的用户。

> 💡 **快速部署**: 如果您只想快速开始，请参考 [README.md](README.md) 的3分钟部署指南

## 🔬 分析类型详细配置

系统提供三种分析类型，您可以根据需求选择：

### 📊 分析类型对比

| 分析类型 | 字数范围 | 适用场景 | 优势 | 适合用户 |
|----------|----------|----------|------|----------|
| **quick** | 200-300字 | • 每日大量论文筛选<br>• 快速了解研究趋势<br>• 初步评估论文价值 | • 节省时间和成本<br>• 突出核心要点<br>• 便于快速决策 | • 需要处理大量论文的研究者<br>• 预算有限的用户<br>• 初级筛选需求 |
| **comprehensive** | 400-600字 | • 日常论文跟踪<br>• 周报和月报<br>• 平衡的分析需求 | • 信息全面均衡<br>• 可读性良好<br>• 性价比最优 | • 大多数研究者（推荐）<br>• 日常学术跟踪<br>• 平衡需求的团队 |
| **detailed** | 600-900字 | • 重要论文深度分析<br>• 学术调研项目<br>• 决策支持分析 | • 技术细节丰富<br>• 深度洞察<br>• 专业评估 | • 资深研究者<br>• 深度技术分析<br>• 投资决策支持 |

### 🎯 推荐配置组合

**🔥 快速筛选模式**（大量论文初筛）：
```bash
ANALYSIS_TYPE=quick
MAX_PAPERS=100
CATEGORIES=cs.AI,cs.LG,cs.CL,cs.CV
ENABLE_PARALLEL=true
MAX_WORKERS=8
```

**⭐ 日常跟踪模式**（推荐）：
```bash
ANALYSIS_TYPE=comprehensive
MAX_PAPERS=50
CATEGORIES=cs.AI,cs.LG,cs.CL
ENABLE_PARALLEL=true
MAX_WORKERS=4
```

**🎓 深度研究模式**（精选论文）：
```bash
ANALYSIS_TYPE=detailed
MAX_PAPERS=20
CATEGORIES=cs.AI,cs.LG
ENABLE_PARALLEL=true
MAX_WORKERS=2
```

### 💰 成本对比

| 分析类型 | 相对成本 | 10篇论文预估 | 50篇论文预估 |
|----------|----------|-------------|-------------|
| quick | 1x | ¥0.05-0.10 | ¥0.25-0.50 |
| comprehensive | 1.5x | ¥0.08-0.15 | ¥0.40-0.75 |
| detailed | 2x | ¥0.10-0.20 | ¥0.50-1.00 |

### ⚙️ 如何配置分析类型

在GitHub Secrets中添加或修改以下配置：

## 🔧 详细配置选项

### Qwen API 配置（推荐）

```bash
# 基础配置
QWEN_API_KEY=your-qwen-api-key      # 必需，阿里云通义千问API密钥
QWEN_MODEL=qwen3-max                # 可选，默认值，可选：qwen3-max, qwen-plus, qwen-turbo

# API 调用优化
API_RETRY_TIMES=3                   # 重试次数
API_DELAY=2                         # 请求间隔(秒)
API_TIMEOUT=60                      # 超时时间(秒)
```

### DeepSeek API 配置

```bash
# 基础配置
DEEPSEEK_API_KEY=sk-your-api-key    # 必需
DEEPSEEK_MODEL=deepseek-chat        # 可选，默认值，这是v3模型，r1模型请使用deepseek-reasoner

# API 调用优化
API_RETRY_TIMES=3                   # 重试次数
API_DELAY=2                         # 请求间隔(秒)
API_TIMEOUT=60                      # 超时时间(秒)
```

### 论文搜索配置

```bash
# 搜索范围
CATEGORIES=cs.AI,cs.LG,cs.CL       # ArXiv分类，支持多个
MAX_PAPERS=50                       # 每次分析论文数量
SEARCH_DAYS=2                       # 搜索最近N天的论文

# 常用分类组合
# AI/ML: cs.AI,cs.LG,cs.CL,cs.CV,cs.IR
# 理论: cs.DS,cs.CC,cs.DM
# 系统: cs.DC,cs.OS,cs.NI
```

### 性能优化

```bash
# 并行处理（推荐开启）
ENABLE_PARALLEL=true               
MAX_WORKERS=4                       # 并行线程数，0=自动计算
BATCH_SIZE=20                       # 批处理大小

# 性能建议：
# - 10篇以下: 串行处理
# - 10-30篇: MAX_WORKERS=2-4
# - 30篇以上: MAX_WORKERS=4-8
```

### 邮件配置

```bash
# Gmail (推荐，我用的是这个，别的没有试过)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=16-digit-app-password  # 应用专用密码

# Outlook
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password

# QQ邮箱
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your-email@qq.com
SMTP_PASSWORD=authorization-code     # 授权码
```

## 📊 成本和性能参考

### Qwen API 成本（推荐）

| 论文数量 | 预估成本(元) | 适用场景 |
|----------|-------------|----------|
| 10篇     | ¥0.02-0.05 | 日常跟踪 |
| 50篇     | ¥0.10-0.25 | 周报总结 |
| 100篇    | ¥0.20-0.50 | 深度调研 |

### DeepSeek API 成本

| 论文数量 | 预估成本(元) | 适用场景 |
|----------|-------------|----------|
| 10篇     | ¥0.10-0.20 | 日常跟踪 |
| 50篇     | ¥0.50-1.00 | 周报总结 |
| 100篇    | ¥1.00-2.00 | 深度调研 |

## 🔍 结果查看

### 邮件报告
- HTML格式，支持移动端查看
- 包含质量评分、创新度、技术严谨性等维度
- 自动发送到指定邮箱

### GitHub Actions日志
- **运行状态**: Actions页面查看每次运行结果
- **详细日志**: 点击具体运行查看详细分析过程
- **错误诊断**: 失败时查看具体错误信息

## 🛠️ 详细故障排除

### Qwen API 问题

**API 密钥无效**
- 检查GitHub Secrets中密钥是否正确
- 登录 [阿里云DashScope控制台](https://dashscope.aliyun.com/) 验证密钥有效性

**余额不足**
- 登录 [阿里云DashScope控制台](https://dashscope.aliyun.com/)
- 查看账户余额和使用统计
- 充值或申请免费额度

**请求频率限制**
```bash
# 在GitHub Secrets中增加请求间隔
API_DELAY=5

# 减少并行数
MAX_WORKERS=2
```

### DeepSeek API 问题

**API 密钥无效**
- 检查GitHub Secrets中密钥格式是否以`sk-`开头
- 登录 [DeepSeek平台](https://platform.deepseek.com/) 验证密钥有效性

**余额不足**
- 登录 [DeepSeek平台](https://platform.deepseek.com/)
- 查看账户余额和使用统计
- 充值或申请免费额度

**请求频率限制**
```bash
# 在GitHub Secrets中增加请求间隔
API_DELAY=5

# 减少并行数
MAX_WORKERS=2
```

### 邮件发送问题

**Gmail 认证失败**
1. 确认启用了两步验证
2. 使用应用专用密码，不是登录密码
3. 检查账户安全设置

**其他邮箱配置**
```bash
# Outlook配置
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587

# QQ邮箱配置
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
```

### GitHub Actions 问题

**Secrets 配置检查**
- Settings → Secrets and variables → Actions
- 确认所有必需的密钥都已添加
- 检查密钥名称拼写是否正确

**权限问题**
- 确认 Fork 的仓库已启用 Actions
- 检查仓库的 Actions 权限设置

**运行超时**
```bash
# 在GitHub Secrets中减少论文数量
MAX_PAPERS=30
```

## 📝 GitHub Actions 最佳实践

### 手动运行配置
在仓库的 Actions 页面可以手动触发运行：
1. 进入 Actions 页面
2. 选择 "Daily Paper Analysis"
3. 点击 "Run workflow"
4. 可以临时修改运行参数

### 修改运行时间
编辑 `.github/workflows/daily_paper_analysis_optimized.yml`：
```yaml
schedule:
  - cron: '0 0 * * *'  # 每日UTC 0:00 (北京时间8:00)
```

### 监控运行状态
- 在 Actions 页面查看历史运行记录
- 设置邮件通知获取运行状态更新
- 查看具体日志了解分析详情

## 🔗 相关文档

- [Qwen API 文档](docs/setup/QWEN_SETUP_GUIDE.md) - 阿里云通义千问API配置
- [DeepSeek API 文档](https://platform.deepseek.com/docs)
- [GitHub Actions 文档](https://docs.github.com/actions)
- [Gmail 应用密码设置](docs/setup/GMAIL_SETUP_GUIDE.md) 
