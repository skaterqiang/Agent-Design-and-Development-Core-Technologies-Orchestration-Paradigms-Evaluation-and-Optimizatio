import json
import random
import os

# 设置系统提示词 - 参考data.py中的医疗顾问prompt
PROMPT = "你是一位精通黄帝内经的中医专家。在回答有关黄帝内经的问题时，请务必遵循循序渐进的原则：先在内部梳理关键信息和可能的风险点（思考过程），再给出专业建议。请注意，任何回答都不能替代实际就医诊断，需强调咨询专业中医师的重要性。"

# 数据路径设置
DATA_PATH = './neijing_data'
INPUT_FILE = r'D:\智能体设计开发实战：核心技术、编排模式、评估与调优\code\chapter-6\6.5.4\neijing_qa_messages_array_20260213_225226.json'

# 设置随机种子以确保可重复性
random.seed(256)

print("[INFO] 开始处理黄帝内经QA数据...")

# 加载原始数据
try:
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    print(f"[SUCCESS] 成功加载 {len(raw_data)} 条原始数据")
except Exception as e:
    print(f"[ERROR] 加载数据失败: {e}")
    exit(1)

# 转换数据格式并添加思考过程
converted_data = []
successful_conversions = 0

for i, item in enumerate(raw_data):
    try:
        # 提取原始messages
        messages = item.get('messages', [])
        
        # 验证数据结构完整性
        if len(messages) < 3:
            print(f"[WARNING] 第{i+1}条数据结构不完整，跳过")
            continue
            
        system_msg = messages[0]
        user_msg = messages[1] 
        assistant_msg = messages[2]
        
        # 验证角色正确性
        if (system_msg.get('role') != 'system' or 
            user_msg.get('role') != 'user' or 
            assistant_msg.get('role') != 'assistant'):
            print(f"[WARNING] 第{i+1}条数据角色不匹配，跳过")
            continue
        
        # 获取原始内容
        user_content = user_msg.get('content', '').strip()
        original_answer = assistant_msg.get('content', '').strip()
        
        # 根据问题内容生成相应的思考过程
        if not user_content or not original_answer:
            print(f"[WARNING] 第{i+1}条数据内容为空，跳过")
            continue
            
        # 智能生成思考过程
        if '年' in user_content and ('老' in user_content or '少' in user_content):
            thinking_process = "此问题涉及人体衰老与生育能力的关系。根据《黄帝内经》理论，需要从肾气充盛、天癸至、气血调和等方面分析年龄与生育能力的关系，同时要考虑男女在生理周期上的差异。"
        elif '道者' in user_content or '寿' in user_content:
            thinking_process = "这是关于养生延年之道理的问题。需要从《黄帝内经》的养生理论出发，分析寿敝天数、中道而立、起居有常等概念，探讨如何通过调节精神、饮食、起居来达到延年益寿的目的。"
        elif '病' in user_content or '疾' in user_content:
            thinking_process = "此为疾病相关问题。根据《黄帝内经》病因病机理论，需要从外感六淫、内伤七情、饮食劳倦等方面分析病因，结合脏腑经络理论判断病位病性。"
        elif '脉' in user_content or '诊' in user_content:
            thinking_process = "这是诊法相关问题。需要运用《黄帝内经》的诊法理论，从望闻问切四诊入手，重点分析脉象变化与脏腑气血的关系。"
        else:
            thinking_process = "根据《黄帝内经》原文及相关理论进行分析，需要综合运用阴阳五行、脏腑经络、气血津液等基础理论来解答此问题。"

        # 构造符合ms-swift格式的新数据项
        new_item = {
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": f"{thinking_process}\n\n{original_answer}"}
            ]
        }
        
        converted_data.append(new_item)
        successful_conversions += 1
        
    except Exception as e:
        print(f"[ERROR] 处理第{i+1}条数据时出错: {e}")
        continue

print(f"[INFO] 成功转换 {successful_conversions} 条数据")

# 随机打乱数据
random.shuffle(converted_data)
print(f"[INFO] 数据已随机打乱")

# 计算分割点，按 9:1 的比例划分训练集（90%）和验证集（10%）
split_idx = int(len(converted_data) * 0.9)
train_data = converted_data[:split_idx]
val_data = converted_data[split_idx:]

print(f"[INFO] 数据分割完成:")
print(f"      训练集大小: {len(train_data)}")
print(f"      验证集大小: {len(val_data)}")

# 创建数据目录
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)
    print(f"[INFO] 创建目录: {DATA_PATH}")

# 保存训练集
train_file = os.path.join(DATA_PATH, 'train.jsonl')
try:
    with open(train_file, 'w', encoding='utf-8') as f:
        for item in train_data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    print(f"[SUCCESS] 训练集已保存到: {train_file}")
except Exception as e:
    print(f"[ERROR] 保存训练集失败: {e}")

# 保存验证集
val_file = os.path.join(DATA_PATH, 'val.jsonl')
try:
    with open(val_file, 'w', encoding='utf-8') as f:
        for item in val_data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    print(f"[SUCCESS] 验证集已保存到: {val_file}")
except Exception as e:
    print(f"[ERROR] 保存验证集失败: {e}")

print("[INFO] 黄帝内经训练数据生成完成!")