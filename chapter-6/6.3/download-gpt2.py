from modelscope import snapshot_download
model_dir = snapshot_download('openai-community/gpt2',cache_dir="D:\\model\\")
print(f'模型已下载至: {model_dir}')
