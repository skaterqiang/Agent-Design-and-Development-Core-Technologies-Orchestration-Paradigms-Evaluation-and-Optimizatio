from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch

model_path = r"D:\model\openai-community\gpt2"

try:
    print(f"正在加载模型: {model_path}")
    # 强制不使用 device_map，直接加载
    tokenizer = GPT2Tokenizer.from_pretrained(model_path)
    model = GPT2LMHeadModel.from_pretrained(model_path, torch_dtype=torch.float32)
    model.to("cuda")
    print("模型加载成功！文件没问题。")
    
    inputs = tokenizer("What is OpenAI？", return_tensors="pt").to("cuda")
    output = model.generate(**inputs, max_new_tokens=20)
    print("推理结果:", tokenizer.decode(output[0]))
    
except Exception as e:
    print("\n[加载失败] 请看下方错误详情：")
    print(e)
    print("\n建议：如果这里也报错且提示 NoneType，请务必检查 config.json 中的 vocab_size 字段。")
