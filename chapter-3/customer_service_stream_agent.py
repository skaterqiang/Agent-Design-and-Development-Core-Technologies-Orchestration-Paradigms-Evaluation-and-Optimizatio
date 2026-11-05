import sys
import os
# 添加当前目录到Python路径（解决通过runpy/ai_profiler等非标准方式运行时的模块导入问题）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'common'))

from customer_service_obj import CustomerServiceAgent, CustomerServiceState
from typing import Optional, List, Dict, Any, Tuple, Generator
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_agent
from datetime import datetime
from langgraph.checkpoint.memory import InMemorySaver
import json
import time
import threading
import concurrent.futures
from statistics import mean, stdev
import asyncio
from config import get_api_key, get_all_configs  # 从上层common导入

# --- 纯流式输出客服代理类 ---
class CustomerServiceStreamAgent(CustomerServiceAgent):
    """
    纯流式客服代理类，只使用 agent.stream() 处理。
    """
    
    def __init__(self, api_key: str, model_name: str = "qwen-max"):
        super().__init__(api_key, model_name)
        
        # 创建支持流式的模型
        self.model = ChatTongyi(
            model_name=model_name,
            streaming=True,
            api_key=api_key
        )
        
        system_prompt = """
你是一个智能客服机器人，专门处理客户咨询和内部员工查询。

## 用户类型和权限：
1. **普通客户 (C端用户)**：可以查询订单状态、比较产品、提交投诉
2. **内部员工 (B端用户)**：除C端功能外，还可以查询销售数据（根据部门权限）

## 核心功能：
1. **订单查询**：帮助用户查询订单状态和物流信息
2. **产品比较**：比较不同产品的参数和特性
3. **投诉处理**：处理客户投诉，包括情感安抚和问题解决
4. **销售数据查询**：为内部员工提供销售数据查询（需要权限）

## 交互原则：
1. 始终保持友好、专业的语气
2. 对客户投诉要先表达共情和道歉
3. 当信息不足时要主动询问
4. 对于复杂问题，适时建议转接人工客服
5. 严格遵循权限控制，不提供无权限访问的信息

## 对话示例：
用户：我的订单123456到哪了？
客服：订单123456（产品：智能手机A）当前状态：已发货，物流状态：运输中...

用户：A手机和B手机哪个拍照更好？
客服：关于智能手机A和智能手机B的拍照对比：智能手机A：像素：5000万...

用户：太差了！刚收到就是坏的！
客服：非常抱歉给您带来这么糟糕的体验！请您提供订单号和商品损坏的照片...
        """
        
        self.agent = create_agent(
            self.model,
            tools=self.tools_list,
            system_prompt=system_prompt,
            state_schema=CustomerServiceState,
            checkpointer=InMemorySaver()
        )
    

    def process_query_stream_with_firstchar_v2(self, user_input: str, user_id: str = "cust001", 
                        reset_state: bool = False) -> Generator[str, None, None]:
        """
        纯流式输出 + 首字响应时间统计。
        """
        user_info = self.USER_PERMISSIONS.get(user_id, {})
        user_type = user_info.get("user_type", "customer")
        department = user_info.get("department", "")
        
        if reset_state or not hasattr(self, 'current_config') or not self.current_config:
            self.current_config = {"configurable": {"thread_id": f"cs-stream-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"}}
        
        if reset_state or not hasattr(self, 'current_state') or not self.current_state:
            self.current_state = {
                "user_id": user_id,
                "user_type": user_type,
                "department": department,
                "conversation_history": [],
                "current_order_id": None,
                "complaint_escalated": False
            }
        
        input_data = {
            "messages": [{"role": "user", "content": user_input}],
            **self.current_state
        }
        
        full_response = ""
        start_time = time.time()
        first_char_time = None
        
        try:
            for chunk in self.agent.stream(
                input_data,
                self.current_config,
                stream_mode="values"
            ):
                if "messages" in chunk:
                    messages = chunk["messages"]
                    if messages:
                        latest_message = messages[-1]
                        
                        # AI消息
                        if (hasattr(latest_message, 'type') and 
                            latest_message.type == 'ai' and 
                            hasattr(latest_message, 'content') and 
                            latest_message.content):
                            content = latest_message.content
                            
                            if first_char_time is None:
                                first_char_time = time.time() - start_time
                            
                            yield content
                            full_response += content
                        
                        # 工具调用消息
                        elif (hasattr(latest_message, 'type') and 
                              latest_message.type == 'tool' and 
                              hasattr(latest_message, 'content')):
                            tool_output = latest_message.content
                            tool_msg = f"\n[工具返回: {tool_output[:50]}...]" if len(tool_output) > 50 else f"\n[工具返回: {tool_output}]"
                            
                            if first_char_time is None:
                                first_char_time = time.time() - start_time
                            
                            yield tool_msg
                            full_response += tool_msg
                
                # 更新状态
                for key in ['current_order_id', 'complaint_escalated', 'conversation_history']:
                    if key in chunk:
                        self.current_state[key] = chunk[key]
            
            self.current_state['conversation_history'] = self.current_state.get('conversation_history', []) + [
                {"user": user_input, "assistant": full_response}
            ]
            
            metadata = {
                "type": "metadata",
                "full_response": full_response,
                "state": self.current_state.copy(),
                "first_char_time": first_char_time if first_char_time is not None else time.time() - start_time
            }
            yield f"__METADATA__:{json.dumps(metadata)}"
            
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            first_char_time = time.time() - start_time if 'start_time' in locals() else 0
            
            yield error_msg
            
            metadata = {
                "type": "error_metadata",
                "full_response": error_msg,
                "state": getattr(self, 'current_state', {}).copy(),
                "first_char_time": first_char_time
            }
            yield f"__METADATA__:{json.dumps(metadata)}"

# 调用代码保持不变
def process_with_metadata(agent, query):
    """处理带有元数据标记的流式输出"""
    import json
    
    print(f"用户: {query}")
    print("客服: ", end="", flush=True)
    
    generator = agent.process_query_stream_with_firstchar_v2(query)
    full_response = ""
    metadata = None
    
    for chunk in generator:
        if chunk.startswith("__METADATA__:"):
            metadata_str = chunk.split("__METADATA__:", 1)[1]
            try:
                metadata = json.loads(metadata_str)
            except json.JSONDecodeError:
                metadata = {"error": "无法解析元数据"}
        else:
            full_response += chunk
            print(chunk, end='', flush=True)
    
    return full_response, metadata

# --- 性能测试用例 ---
def single_test(agent):
    """单次测试"""
    print("\n" + "="*60)
    print("🧪 单次性能测试")
    print("="*60)
    
    start_time = time.time()
    response, metadata = process_with_metadata(agent, "我的订单123456到哪了？")
    total_time = time.time() - start_time
    
    print(f"\n✅ 单次测试完成")
    print(f"   总耗时: {total_time:.3f}秒")
    print(f"   首字时间: {metadata.get('first_char_time', 0):.3f}秒")
    print(f"   响应长度: {len(response)}字符")
    
    return total_time, metadata.get('first_char_time', 0)

def batch_test(agent, num_queries=10):
    """批量测试"""
    print("\n" + "="*60)
    print(f"🧪 批量性能测试 (N={num_queries})")
    print("="*60)
    
    test_queries = [
        "我的订单123456到哪了？",
        "A手机和B手机哪个拍照更好？",
        "太差了！刚收到就是坏的！",
        "请查询今天的销售数据",
        "订单789012物流状态如何？",
        "产品C的价格是多少？",
        "如何退货？",
        "客服你好，我想投诉",
        "员工权限查询销售额",
        "明天订单能到吗？"
    ]
    
    total_times = []
    first_char_times = []
    
    batch_start = time.time()
    for i in range(num_queries):
        query = test_queries[i % len(test_queries)]
        agent.set_user(f"cust{i+1:03d}")
        
        start_time = time.time()
        _, metadata = process_with_metadata(agent, query)
        total_time = time.time() - start_time
        
        total_times.append(total_time)
        first_char_times.append(metadata.get('first_char_time', 0))
        
        print(f"  第{i+1:2d}次: {total_time:.3f}s (首字: {metadata.get('first_char_time', 0):.3f}s)")
    
    batch_total_time = time.time() - batch_start
    
    print(f"\n📊 批量测试统计:")
    print(f"   平均总耗时: {mean(total_times):.3f}±{stdev(total_times):.3f}秒")
    print(f"   平均首字时间: {mean(first_char_times):.3f}±{stdev(first_char_times):.3f}秒")
    print(f"   总批量耗时: {batch_total_time:.3f}秒")
    print(f"   QPS: {num_queries/batch_total_time:.2f}")
    
    return {
        'avg_total': mean(total_times),
        'std_total': stdev(total_times),
        'avg_first': mean(first_char_times),
        'std_first': stdev(first_char_times),
        'qps': num_queries/batch_total_time
    }

def concurrent_test(agent, num_concurrent=5, num_queries_per_thread=3):
    """并行压力测试"""
    print("\n" + "="*60)
    print(f"🧪 并行压力测试 (并发={num_concurrent}, 每线程={num_queries_per_thread})")
    print("="*60)
    
    test_queries = [
        "我的订单123456到哪了？",
        "A手机和B手机哪个拍照更好？",
        "太差了！刚收到就是坏的！"
    ]
    
    results = []
    lock = threading.Lock()
    
    def worker_thread(thread_id):
        local_agent = CustomerServiceStreamAgent(api_key=API_KEY)  # 每个线程独立agent
        local_results = []
        
        for i in range(num_queries_per_thread):
            query = test_queries[i % len(test_queries)]
            local_agent.set_user(f"conc{thread_id:03d}-{i+1:03d}")
            
            start_time = time.time()
            _, metadata = process_with_metadata(local_agent, query)
            total_time = time.time() - start_time
            
            local_results.append({
                'total_time': total_time,
                'first_char_time': metadata.get('first_char_time', 0),
                'thread_id': thread_id,
                'query_idx': i
            })
        
        with lock:
            results.extend(local_results)
            print(f"  线程{thread_id:2d}完成 {num_queries_per_thread}个查询")
    
    # 启动并发测试
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(worker_thread, i) for i in range(num_concurrent)]
        concurrent.futures.wait(futures)
    
    total_time = time.time() - start_time
    total_queries = num_concurrent * num_queries_per_thread
    
    total_times = [r['total_time'] for r in results]
    first_char_times = [r['first_char_time'] for r in results]
    
    print(f"\n📊 并行测试统计:")
    print(f"   总查询数: {total_queries}")
    print(f"   总耗时: {total_time:.3f}秒")
    print(f"   总体QPS: {total_queries/total_time:.2f}")
    print(f"   平均单查询耗时: {mean(total_times):.3f}±{stdev(total_times):.3f}秒")
    print(f"   平均首字时间: {mean(first_char_times):.3f}±{stdev(first_char_times):.3f}秒")
    
    return {
        'total_queries': total_queries,
        'total_time': total_time,
        'qps': total_queries/total_time,
        'avg_total': mean(total_times),
        'std_total': stdev(total_times),
        'avg_first': mean(first_char_times),
        'std_first': stdev(first_char_times)
    }

if __name__ == "__main__":
    # ✅ 从common/config.py获取API密钥
    try:
        API_KEY = get_api_key("tongyi")
        print("🔑 API配置加载成功")
        print("配置信息:", get_all_configs())
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
        sys.exit(1)
    
    print("🚀 客服流式代理性能测试系统")
    print("="*60)
    
    # 创建测试agent
    agent = CustomerServiceStreamAgent(api_key=API_KEY)
    agent.set_user("cust001")
    
    # 1. 单次测试
    single_total, single_first = single_test(agent)
    
    # 2. 批量测试
    batch_stats = batch_test(agent, num_queries=10)
    
    # 3. 并行压力测试
    concurrent_stats = concurrent_test(agent, num_concurrent=5, num_queries_per_thread=3)
    
    # 4. 综合报告
    print("\n" + "="*60)
    print("📈 综合性能报告")
    print("="*60)
    print(f"单次测试: 总耗时 {single_total:.3f}s | 首字 {single_first:.3f}s")
    print(f"批量测试: 平均 {batch_stats['avg_total']:.3f}±{batch_stats['std_total']:.3f}s | QPS {batch_stats['qps']:.2f}")
    print(f"并行测试: QPS {concurrent_stats['qps']:.2f} | 平均 {concurrent_stats['avg_total']:.3f}±{concurrent_stats['std_total']:.3f}s")
    
    print("\n✅ 所有测试完成！")
