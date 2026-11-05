# langgraph_workflow_rag.py
from typing import TypedDict, List, Annotated, Optional
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sys
import os

# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key

# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")

# 定义LangGraph状态结构
class RAGState(TypedDict):
    """定义RAG工作流的状态"""
    query: str                     # 用户查询
    documents: List[Document]      # 检索到的文档
    context: str                   # 提取的上下文
    answer: Optional[str]          # 生成的答案
    history: Annotated[List[str], operator.add]  # 对话历史

# 步骤 1: 准备文档
def load_and_split_documents():
    sample_text = """
    LangChain 是一个由大型语言模型(LLM)驱动的应用框架。
    它使应用能够连接到各种数据源来获取数据以进行分析。
    LangChain 通过链(Chain)组件将多个调用连接在一起，创建序列化的工作流。
    Agents 可以使用工具和进行推理来做出决策和采取行动。
    Retrieval-Augmented Generation (RAG) 是一种增强 LLM 能力的方法。
    """
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20
    )
    
    chunks = text_splitter.split_text(sample_text)
    documents = [Document(page_content=chunk) for chunk in chunks]
    return documents

# 步骤 2: 创建向量存储
def create_faiss_vectorstore(documents):
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=API_KEY
    )
    
    vector_store = FAISS.from_documents(
        documents=documents,
        embedding=embeddings
    )
    
    return vector_store

# 步骤 3: 创建检索器
def create_retriever(vector_store):
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 2}
    )

# 初始化全局资源
print("正在初始化资源...")
documents = load_and_split_documents()
vector_store = create_faiss_vectorstore(documents)
retriever = create_retriever(vector_store)

# 初始化LLM和提示模板
llm = ChatTongyi(
    model_name="qwen-max",
    dashscope_api_key=API_KEY
)

# 提示模板
rag_prompt = ChatPromptTemplate.from_template(
    "使用以下检索到的上下文来回答问题。如果你不知道答案，请如实说明。\n\n"
    "上下文:\n{context}\n\n"
    "历史对话:\n{history}\n\n"
    "问题: {question}\n\n"
    "回答:"
)

# LangGraph 节点函数
def retrieve_documents(state: RAGState):
    """检索节点：从向量存储中获取相关文档"""
    print(f"[检索节点] 正在检索文档，查询: {state['query']}")
    
    # 执行检索
    docs = retriever.invoke(state['query'])
    
    # 更新状态
    return {
        "documents": docs,
        "context": "\n".join([doc.page_content for doc in docs])
    }

def generate_answer(state: RAGState):
    """生成节点：基于上下文生成答案"""
    print(f"[生成节点] 正在生成答案，上下文长度: {len(state['context'])}")
    
    # 构建提示
    prompt_input = {
        "context": state['context'],
        "question": state['query'],
        "history": "\n".join(state.get('history', []))
    }
    
    # 调用LLM生成答案
    prompt_value = rag_prompt.invoke(prompt_input)
    response = llm.invoke(prompt_value)
    
    # 解析输出
    answer = StrOutputParser().invoke(response)
    
    # 更新状态
    return {
        "answer": answer,
        "history": [f"用户: {state['query']}", f"助手: {answer}"]
    }

def validate_query(state: RAGState):
    """验证节点：检查查询是否有效"""
    query = state.get('query', '').strip()
    
    if not query:
        return {"answer": "请输入有效的问题。"}
    
    if len(query) < 2:
        return {"answer": "问题太短，请提供更多细节。"}
    
    return {}

def route_after_validation(state: RAGState):
    """路由节点：根据验证结果决定下一步"""
    if state.get('answer'):
        # 如果已经有答案（验证失败），直接结束
        return END
    else:
        # 验证成功，继续检索
        return "retrieve_documents"

def create_rag_graph():
    """创建RAG工作流图"""
    # 创建图构建器
    workflow = StateGraph(RAGState)
    
    # 添加节点
    workflow.add_node("validate_query", validate_query)
    workflow.add_node("retrieve_documents", retrieve_documents)
    workflow.add_node("generate_answer", generate_answer)
    
    # 添加边（定义流程）
    workflow.add_edge(START, "validate_query")
    workflow.add_conditional_edges(
        "validate_query",
        route_after_validation,
        {
            END: END,
            "retrieve_documents": "retrieve_documents"
        }
    )
    workflow.add_edge("retrieve_documents", "generate_answer")
    workflow.add_edge("generate_answer", END)
    # 创建MemorySaver实例
    checkpointer = MemorySaver()
    # 编译图 - 使用 checkpointer 参数而不是 memory
    app = workflow.compile(checkpointer=checkpointer)  # Changed from memory= to checkpointer=
    return app

# 主函数
def main():
    # 创建RAG图
    print("正在创建RAG工作流图...")
    app = create_rag_graph()
    
    # 配置对话线程（支持多轮对话）
    thread_config = {"configurable": {"thread_id": "rag-example-1"}}
    
    # 示例查询
    queries = [
        "LangChain 是什么？",
        "什么是 Agents？",
        "RAG 是什么意思？",
        "",  # 空查询（用于测试验证）
        "简要总结一下"  # 测试历史对话
    ]
    
    for i, query in enumerate(queries):
        print(f"\n{'='*60}")
        print(f"第 {i+1} 轮查询: {query if query else '(空查询)'}")
        print('-'*60)
        
        # 初始化或更新状态
        initial_state = {"query": query, "history": []}
        
        # 执行图
        try:
            # 同步调用
            final_state = app.invoke(initial_state, thread_config)
            
            if final_state.get("answer"):
                print(f"回答:\n{final_state['answer']}")
            else:
                print("未生成答案。")
                
        except Exception as e:
            print(f"执行出错: {e}")
    
    # 显示图结构
    print(f"\n{'='*60}")
    print("工作流图结构:")
    try:
        print(app.get_graph().draw_ascii())
    except:
        try:
            # 尝试ASCII格式
            print(app.get_graph().draw_ascii())
        except:
            print("无法显示图结构，但工作流已创建成功。")

if __name__ == "__main__":
    main()
