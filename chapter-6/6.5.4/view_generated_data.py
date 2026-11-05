import json

# 查看训练集第一条数据
with open(r'D:\智能体设计开发实战：核心技术、编排模式、评估与调优\code\neijing_data\train.jsonl', 'r', encoding='utf-8') as f:
    first_line = f.readline()
    data = json.loads(first_line)
    print("训练集第一条数据:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

print("\n" + "="*50 + "\n")

# 查看验证集第一条数据
with open(r'D:\智能体设计开发实战：核心技术、编排模式、评估与调优\code\neijing_data\val.jsonl', 'r', encoding='utf-8') as f:
    first_line = f.readline()
    data = json.loads(first_line)
    print("验证集第一条数据:")
    print(json.dumps(data, ensure_ascii=False, indent=2))