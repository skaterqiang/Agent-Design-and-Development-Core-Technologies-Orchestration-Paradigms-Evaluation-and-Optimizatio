cd /path/to/trip
langgraph dev --port 2024

cd /path/to/flight
langgraph dev --port 2025

curl --request POST \
  --url 127.0.0.1:2024/assistants/search \
  --header 'Content-Type: application/json' \
  --data '{"limit": 10, "offset": 0}'


  curl --request POST \
  --url 127.0.0.1:2025/assistants/search \
  --header 'Content-Type: application/json' \
  --data '{"limit": 10, "offset": 0}'

pip install -i https://pypi.tuna.tsinghua.edu.cn/simple langgraph langchain langchain_community dashscope langchain_openai langgraph-cli