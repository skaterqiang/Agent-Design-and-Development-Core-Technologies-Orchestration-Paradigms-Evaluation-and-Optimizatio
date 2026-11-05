import json
import glob
import os
import re
import sys

# 读取生成的messages格式文件
# convert_to_messages_format.py 会按运行时间生成 neijing_qa_messages_<时间戳>.jsonl，
# 时间戳每次运行都不同，因此这里自动匹配当前目录下最新的一个，而不是写死文件名。
# 仅匹配纯 messages 文件（时间戳形如 20260213_224945），排除 _with_chapter_ 等变体。
_HERE = os.path.dirname(os.path.abspath(__file__))
_candidates = [
    p for p in glob.glob(os.path.join(_HERE, 'neijing_qa_messages_*.jsonl'))
    if re.search(r'neijing_qa_messages_\d{8}_\d{6}\.jsonl$', p)
]
if not _candidates:
    print("未找到 neijing_qa_messages_<时间戳>.jsonl，请先运行 convert_to_messages_format.py 生成数据。")
    sys.exit(1)
_input_file = max(_candidates, key=os.path.getmtime)
print(f"验证文件: {os.path.basename(_input_file)}")

with open(_input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("验证Messages格式数据:")
print("="*50)

# 检查前3个样本
for i, line in enumerate(lines[:3]):
    try:
        data = json.loads(line.strip())
        print(f"\n样本 {i+1}:")
        print(f"数据结构: {list(data.keys())}")
        
        if 'messages' in data:
            messages = data['messages']
            print(f"Messages数量: {len(messages)}")
            
            for j, msg in enumerate(messages):
                print(f"  Message {j+1}:")
                print(f"    Role: {msg.get('role', 'N/A')}")
                print(f"    Content length: {len(msg.get('content', ''))} characters")
                if j == 0:  # 显示system prompt
                    print(f"    Content preview: {msg.get('content', '')[:50]}...")
                elif j == 1:  # 显示user question
                    print(f"    Content preview: {msg.get('content', '')[:50]}...")
        
        print("-" * 30)
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")

print(f"\n总计验证样本数: {len(lines)}")