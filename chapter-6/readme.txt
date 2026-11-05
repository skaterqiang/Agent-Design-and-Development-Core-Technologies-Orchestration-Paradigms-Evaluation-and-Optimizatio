# 1. 安装venv支持包和pip
sudo apt install -y python3-pip
sudo apt install -y python3.12-venv
# 2. 创建虚拟环境
python3 -m venv ~/vllm-venv
# 3. 激活虚拟环境
source ~/vllm-venv/bin/activate
# 4. 安装uv
pip install uv -i https://mirrors.aliyun.com/pypi/simple/
# 5. 设置下载超时
export UV_HTTP_TIMEOUT=360
# 6. 使用uv安装vllm和魔搭社区库
uv pip install vllm -i https://mirrors.aliyun.com/pypi/simple/
uv pip install modelscope -i https://mirrors.aliyun.com/pypi/simple/
