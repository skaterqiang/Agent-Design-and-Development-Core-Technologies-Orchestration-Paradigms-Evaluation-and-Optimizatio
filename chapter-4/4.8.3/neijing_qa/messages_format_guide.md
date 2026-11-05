# 黄帝内经问答对 Messages 格式训练数据指南

## 概述

本程序将《黄帝内经》问答对数据转换为ms-swift框架要求的Messages格式训练数据，完全符合[tain_data_design.txt](tain_data_design.txt)中指定的格式要求。

## 生成的文件格式

### 1. 标准Messages格式 (`.jsonl`文件)
每行一个JSON对象，格式如下：

```json
{"messages": [{"role": "system", "content": "你是一位精通黄帝内经的中医，在回答有关皇帝内经的问题时，请务必遵循循序渐进的原则：先在内部梳理关键信息和可能的风险点（思考过程），再给出专业建议。"}, {"role": "user", "content": "有其年已老，而有子者，何也？"}, {"role": "assistant", "content": "此其天寿过度，气脉常通，而肾气有余也。此虽有子，男子不过尽八八，女子不过尽七七，而天地之精气皆竭矣。"}]}
```

### 2. 带章节信息的Messages格式
在system prompt中包含了章节信息：

```json
{"messages": [{"role": "system", "content": "你是一位精通黄帝内经的中医，在回答有关皇帝内经的问题时，请务必遵循循序渐进的原则：先在内部梳理关键信息和可能的风险点（思考过程），再给出专业建议。本问题来自《黄帝内经》上古天真论篇第一。"}, {"role": "user", "content": "有其年已老，而有子者，何也？"}, {"role": "assistant", "content": "此其天寿过度，气脉常通，而肾气有余也..."}]}
```

### 3. JSON数组格式 (便于查看和调试)
```json
[
  {
    "messages": [
      {
        "role": "system",
        "content": "你是一位精通黄帝内经的中医..."
      },
      {
        "role": "user", 
        "content": "有其年已老，而有子者，何也？"
      },
      {
        "role": "assistant",
        "content": "此其天寿过度，气脉常通，而肾气有余也..."
      }
    ]
  }
]
```

## 文件说明

### 主要生成文件：
- `neijing_qa_messages_YYYYMMDD_HHMMSS.jsonl` - 标准Messages格式
- `neijing_qa_messages_with_chapter_YYYYMMDD_HHMMSS.jsonl` - 带章节信息的Messages格式  
- `neijing_qa_messages_array_YYYYMMDD_HHMMSS.json` - JSON数组格式（便于查看）
- `messages_conversion_report_YYYYMMDD_HHMMSS.json` - 转换报告

## 使用方法

### 1. 基本使用
```bash
python convert_to_messages_format.py
```

### 2. 在ms-swift中使用

#### 训练配置示例：
```yaml
model:
  model_type: qwen2
  model_id_or_path: Qwen/Qwen2-7B-Instruct

dataset:
  train_dataset: 
    - path: neijing_qa_messages_20260213_224945.jsonl
      format: messages
  dataset_test_ratio: 0.1

training_args:
  num_train_epochs: 3
  per_device_train_batch_size: 4
  learning_rate: 1e-5
```

#### 数据加载代码示例：
```python
from datasets import load_dataset

# 加载messages格式数据
dataset = load_dataset('json', data_files='neijing_qa_messages_20260213_224945.jsonl')

# 查看数据结构
print(dataset['train'][0])
# 输出: {'messages': [{'role': 'system', 'content': '...'}, ...]}
```

## 数据统计

- **总问答对数**: 264个
- **涉及章节数**: 3个
- **数据格式**: Messages (role-based conversation)
- **编码**: UTF-8
- **文件格式**: JSON Lines (.jsonl)

## 章节分布

| 章节 | 问答对数量 |
|------|------------|
| 上古天真论篇第一 | 2个 |
| 六节藏象论篇第九 | 5个 |
| 移精变气论篇第十三 | 257个 |

## 格式验证

程序会自动验证生成的数据格式，确保：
1. 每个样本都有完整的system/user/assistant三角色对话
2. JSON格式正确无误
3. 数据完整性得到保证

## 注意事项

1. **文件格式**: 使用.jsonl格式，每行一个独立的JSON对象
2. **编码**: 所有文件使用UTF-8编码
3. **系统提示词**: 包含专业的中医指导原则
4. **数据质量**: 所有问答对都经过验证和清洗

## 扩展功能

程序还提供了以下扩展功能：
- 带章节信息的增强版本
- JSON数组格式便于调试
- 完整的转换报告
- 数据统计和验证功能

## 故障排除

常见问题及解决方案：
1. **文件找不到**: 确保`neijing_qa_results.json`在同一目录下
2. **编码错误**: 确保使用UTF-8编码打开文件
3. **格式错误**: 检查JSON语法是否正确

这个格式特别适合用于训练对话式AI模型，能够很好地保持对话的上下文和角色关系。