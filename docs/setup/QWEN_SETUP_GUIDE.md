# 阿里云通义千问（Qwen）API配置指南

本指南将帮助您设置阿里云通义千问（Qwen）API密钥，以便在论文分析系统中使用。

## 1. 注册阿里云账号

1. 访问 [阿里云官网](https://www.aliyun.com/)
2. 点击"免费注册"创建新账号
3. 完成身份验证和账号激活

## 2. 开通DashScope服务

1. 登录阿里云控制台
2. 搜索"DashScope"服务或访问 [DashScope控制台](https://dashscope.aliyun.com/)
3. 点击"立即开通"按钮
4. 完成服务开通流程

## 3. 获取API密钥

1. 在DashScope控制台中，进入"API-KEY管理"
2. 点击"创建新的API-KEY"
3. 复制生成的API密钥并妥善保存

## 4. 配置API密钥

在GitHub仓库的Settings → Secrets and variables → Actions中添加以下密钥：

```
QWEN_API_KEY=your-qwen-api-key
QWEN_MODEL=qwen3-max                   # 可选，默认为qwen3-max
```

## 5. API使用建议

### 推荐的模型：
- `qwen3-max`：适用于复杂、多步骤的任务
- `qwen-plus`：在效果和成本之间取得平衡
- `qwen-turbo`：适用于简单、快速的任务

### 成本优化：
- 根据任务复杂度选择合适的模型
- 监控API使用量和费用

## 6. 测试配置

配置完成后，您可以运行以下命令测试API连接：

```bash
make validate-env
```

## 7. 常见问题

**API密钥无效？**
- 确认API密钥格式正确
- 检查DashScope服务是否已开通

**API调用失败？**
- 检查API密钥是否有足够的权限
- 确认API密钥未过期或被禁用

**费用管理**
- 阿里云提供免费额度，可在控制台查看
- 建议设置消费提醒，控制成本

## 8. 技术支持

如遇技术问题：
- 查阅 [阿里云官方文档](https://help.aliyun.com/)
- 访问 [DashScope开发者社区](https://developer.aliyun.com/group/dashscope)