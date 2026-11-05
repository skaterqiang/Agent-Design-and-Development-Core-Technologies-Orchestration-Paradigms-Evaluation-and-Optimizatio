from modelscope import snapshot_download
model_dir = snapshot_download('Qwen/Qwen3-0.6B-Base',cache_dir="D:\\model\\")
print(f'模型已下载至: {model_dir}')
