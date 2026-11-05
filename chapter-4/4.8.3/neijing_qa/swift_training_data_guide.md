# 黄帝内经问答对 ms-swift 训练数据格式转换指南

## 概述

本程序将《黄帝内经》问答对数据转换为ms-swift框架支持的多种训练数据格式，便于进行中医领域的语言模型微调。

## 生成的文件格式

### 1. Alpaca格式 (`neijing_qa_alpaca_*.json`)
```json
{
  "instruction": "请根据《黄帝内经》上古天真论篇第一的内容回答以下中医问题：",
  "input": "有其年已老，而有子者，何也？",
  "output": "此其天寿过度，气脉常通，而肾气有余也..."
}
```

### 2. ShareGPT格式 (`neijing_qa_sharegpt_*.json`)
```json
{
  "conversations": [
    {
      "from": "human",
      "value": "《黄帝内经》上古天真论篇第一中提到：有其年已老，而有子者，何也？"
    },
    {
      "from": "gpt",
      "value": "此其天寿过度，气脉常通，而肾气有余也..."
    }
  ]
}
```

### 3. ChatML格式 (`neijing_qa_chatml_*.json`)
```json
{
  "prompt": "<|system|>
你是一位精通《黄帝内经》的中医专家，请根据经典内容准确回答相关问题。<|endoftext|>
<|user|>
《黄帝内经》上古天真论篇第一中记载：有其年已老，而有子者，何也？<|endoftext|>
<|assistant|>",
  "completion": "此其天寿过度，气脉常通，而肾气有余也...<|endoftext|>"
}
```

### 4. Instruction格式 (`neijing_qa_instruction_*.json`)
```json
{
  "text": "Instruction: 作为一名中医专家，请根据《黄帝内经》上古天真论篇第一回答以下问题
Input: 有其年已老，而有子者，何也？
Output: 此其天寿过度，气脉常通，而肾气有余也..."
}
```

## 使用方法

### 1. 基本使用
```bash
python convert_to_swift_format.py
```

### 2. 自定义输出目录
修改程序中的 `convert_all_formats()` 方法参数：
```python
converter.convert_all_formats(output_dir="your/custom/path")
```

## 数据统计

- **总问答对数**: 264个
- **涉及章节数**: 3个
- **章节分布**:
  - 上古天真论篇第一: 2个问答对
  - 六节藏象论篇第九: 5个问答对  
  - 移精变气论篇第十三: 257个问答对

## ms-swift训练配置示例

### Alpaca格式训练配置
```yaml
model:
  model_type: qwen2
  model_id_or_path: Qwen/Qwen2-7B-Instruct

dataset:
  train_dataset:
    - neijing_qa_alpaca_20260213_223524.json
  dataset_test_ratio: 0.1

training_args:
  num_train_epochs: 3
  per_device_train_batch_size: 4
  learning_rate: 1e-5
```

### ShareGPT格式训练配置
```yaml
model:
  model_type: qwen2
  model_id_or_path: Qwen/Qwen2-7B-Instruct

dataset:
  train_dataset:
    - neijing_qa_sharegpt_20260213_223524.json
  dataset_test_ratio: 0.1
  dataset_format: sharegpt

training_args:
  num_train_epochs: 3
  per_device_train_batch_size: 4
```

## 注意事项

1. **数据质量**: 所有问答对都经过验证，确保内容完整性和准确性
2. **章节信息**: 每个问答对都包含来源章节信息，便于追溯
3. **编码格式**: 所有文件均使用UTF-8编码，确保中文正确显示
4. **时间戳**: 文件名包含时间戳，便于版本管理

## 文件清单

生成的主要文件：
- `neijing_qa_alpaca_*.json` - Alpaca格式训练数据
- `neijing_qa_sharegpt_*.json` - ShareGPT格式训练数据  
- `neijing_qa_chatml_*.json` - ChatML格式训练数据
- `neijing_qa_instruction_*.json` - Instruction格式训练数据
- `conversion_report_*.json` - 转换报告

## 技术细节

- **输入源**: `neijing_qa_results.json`
- **处理方式**: JSON解析 → 格式转换 → 文件输出
- **错误处理**: 完善的异常捕获和日志记录
- **兼容性**: 支持Windows/Linux/macOS环境

## 扩展建议

1. 可根据需要添加其他格式支持
2. 可增加数据清洗和预处理功能
3. 可添加数据增强和扩充功能
4. 可集成自动化的训练流程