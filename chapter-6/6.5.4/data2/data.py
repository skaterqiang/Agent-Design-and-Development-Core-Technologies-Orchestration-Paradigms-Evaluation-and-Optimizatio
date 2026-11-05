from modelscope.msdatasets import MsDataset
import json
import random
import os

PROMPT = "你是一位专业的医疗顾问。在回答用户关于健康、疾病、药物等方面的问题时，请务必遵循循序渐进的原则：先在内部梳理关键信息和可能的风险点（思考过程），再给出专业建议。请注意，任何回答都不能替代实际就医诊断，需强调咨询医生的重要性。"
DATA_PATH = './data'

# 设置随机种子以确保可重复性
random.seed(256)

# 加载数据集
ds = MsDataset.load('krisfu/delicate_medical_r1_data', subset_name='default', split='train')

# 将数据集转换为列表
data_list = list(ds)

# 随机打乱数据
random.shuffle(data_list)

# 计算分割点，按 9:1 的比例划分训练集（90%）和验证集（10%）。
split_idx = int(len(data_list) * 0.9)

# 分割数据
train_data = data_list[:split_idx]
val_data = data_list[split_idx:]

# 保存成ms-swift标准数据集格式
# 这是 ms-swift 框架要求的多轮对话格式：
# system：系统指令（角色设定）
# user：用户输入
# assistant：模型回答
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)
"""
{"messages": [
    {"role": "system", "content": "<system>"}, 
    {"role": "user", "content": "<query1>"}, 
    {"role": "assistant", "content": "<response1>"}, 
]}
"""
# 保存训练集
with open(os.path.join(DATA_PATH,'train.jsonl'), 'w', encoding='utf-8') as f:
    for item in train_data:
        system_content = PROMPT
        user_content = item['question']
        assistant_content = f'<think>{item["think"]}</think> \n {item["answer"]}'
        json.dump({
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content}
            ]
        }, f, ensure_ascii=False)
        f.write('\n')

# 保存验证集
with open(os.path.join(DATA_PATH,'val.jsonl'), 'w', encoding='utf-8') as f:
    for item in val_data:
        system_content = PROMPT
        user_content = item['question']
        assistant_content = f'<think>{item["think"]}</think> \n {item["answer"]}'
        json.dump({
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content}
            ]
        }, f, ensure_ascii=False)
        f.write('\n')


print(f"数据集已分割完成：")
print(f"训练集大小：{len(train_data)}")
print(f"验证集大小：{len(val_data)}")
