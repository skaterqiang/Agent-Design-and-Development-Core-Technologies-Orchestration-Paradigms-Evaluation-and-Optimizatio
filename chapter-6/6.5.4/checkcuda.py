import torch
print(torch.__version__)
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
print(f"Supports bfloat16: {torch.cuda.is_bf16_supported()}")
