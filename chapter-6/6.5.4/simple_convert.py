import json
import random
import os

print("开始转换黄帝内经数据...")

# 加载数据
with open(r'D:\智能体设计开发实战：核心技术、编排模式、评估与调优\code\chapter-6\6.5.4\neijing_qa_messages_array_20260213_225226.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"加载了 {len(data)} 条数据")

# 转换格式
new_data = []
for item in data:
    messages = item['messages']
    user_content = messages[1]['content']
    assistant_content = messages[2]['content']
    
    # 添加思考过程
    thinking = "根据《黄帝内经》理论分析此问题..."
    new_assistant = f"{thinking}\n\n{assistant_content}"
    
    new_item = {
        "messages": [
            {"role": "system", "content": "你是一位精通黄帝内经的中医专家"},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": new_assistant}
        ]
    }
    new_data.append(new_item)

# 分割数据
random.seed(256)
random.shuffle(new_data)
split_idx = int(len(new_data) * 0.9)
train_data = new_data[:split_idx]
val_data = new_data[split_idx:]

print(f"训练集: {len(train_data)}, 验证集: {len(val_data)}")

# 保存数据
os.makedirs('./neijing_data', exist_ok=True)

with open('./neijing_data/train.jsonl', 'w', encoding='utf-8') as f:
    for item in train_data:
        json.dump(item, f, ensure_ascii=False)
        f.write('\n')

with open('./neijing_data/val.jsonl', 'w', encoding='utf-8') as f:
    for item in val_data:
        json.dump(item, f, ensure_ascii=False)
        f.write('\n')

print("转换完成!")