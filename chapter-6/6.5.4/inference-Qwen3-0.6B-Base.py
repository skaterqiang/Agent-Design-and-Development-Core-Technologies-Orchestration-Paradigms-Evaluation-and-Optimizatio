from transformers import GPT2LMHeadModel, GPT2Tokenizer, AutoModelForCausalLM, AutoTokenizer
import torch
import os

model_path = r"D:\model\Qwen\Qwen3-0.6B-Base"

def check_gpu_availability():
    """检查GPU可用性"""
    if torch.cuda.is_available():
        print(f"检测到 {torch.cuda.device_count()} 个GPU:")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        return True
    else:
        print("未检测到GPU")
        return False

def load_model_with_fallback(model_path):
    """尝试多种方式加载模型"""
    print(f"正在加载模型: {model_path}")
    
    # 首先检查模型配置
    config_path = os.path.join(model_path, "config.json")
    if os.path.exists(config_path):
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        model_type = config.get('model_type', 'unknown')
        print(f"模型类型: {model_type}")
        
        # 如果是Qwen模型，使用Auto类
        if 'qwen' in model_type.lower():
            print("检测到Qwen模型，使用Auto类加载...")
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_path)
                if torch.cuda.is_available():
                    model = AutoModelForCausalLM.from_pretrained(
                        model_path, 
                        torch_dtype=torch.bfloat16,
                        device_map="auto"
                    )
                    device = "cuda"
                else:
                    model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        torch_dtype=torch.float32,
                        low_cpu_mem_usage=True
                    )
                    device = "cpu"
                    model.to(device)
                return model, tokenizer, device, True
            except Exception as e:
                print(f"Auto类加载失败: {e}")
    
    # 回退到GPT2类（可能会失败）
    print("尝试使用GPT2类加载...")
    try:
        tokenizer = GPT2Tokenizer.from_pretrained(model_path)
        if torch.cuda.is_available():
            model = GPT2LMHeadModel.from_pretrained(model_path, torch_dtype=torch.float32)
            model.to("cuda")
            device = "cuda"
        else:
            model = GPT2LMHeadModel.from_pretrained(model_path, torch_dtype=torch.float32)
            device = "cpu"
        return model, tokenizer, device, False
    except Exception as e:
        raise e

try:
    print("=" * 50)
    print("模型推理测试")
    print("=" * 50)
    
    # 检查GPU
    gpu_available = check_gpu_availability()
    
    # 加载模型
    model, tokenizer, device, is_auto_loaded = load_model_with_fallback(model_path)
    
    print(f"模型加载成功！")
    print(f"使用的设备: {device}")
    print(f"加载方式: {'Auto类' if is_auto_loaded else 'GPT2类'}")
    
    # 测试推理
    test_input = "何谓从则生，逆则死？"
    print(f"\n输入文本: {test_input}")
    
    inputs = tokenizer(test_input, return_tensors="pt").to(device)
    
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=30,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    result = tokenizer.decode(output[0], skip_special_tokens=True)
    print(f"推理结果: {result}")
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)
    
except Exception as e:
    print("\n[加载失败] 请看下方错误详情：")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {str(e)}")
    
    print("\n建议解决方案：")
    if "FP8" in str(e) or "quantization" in str(e):
        print("1. FP8量化需要GPU支持，请确认CUDA环境")
        print("2. 可以尝试使用非量化的模型版本")
    elif "tokenizer" in str(e).lower() or "gpt2" in str(e).lower():
        print("1. 模型类型与tokenizer不匹配")
        print("2. 建议使用对应的模型类加载")
    elif "vocab_size" in str(e):
        print("1. 检查config.json中的vocab_size字段")
        print("2. 确认模型文件完整性")
    else:
        print("1. 检查模型路径是否正确")
        print("2. 确认所需依赖包已安装")
        print("3. 查看完整错误堆栈信息")
    
    import traceback
    print("\n详细错误堆栈：")
    traceback.print_exc()