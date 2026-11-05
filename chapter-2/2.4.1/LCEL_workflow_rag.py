# LCEL_workflow_rag.py
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")

# 步骤 1: 准备文档（加载和分割）
def load_and_split_documents():
    # 如果有多个文本文件可以加载
    documents = []
    
    # 示例：使用简单文本而不是加载文件
    sample_text = """
    LangChain 是一个由大型语言模型(LLM)驱动的应用框架。
    它使应用能够连接到各种数据源来获取数据以进行分析。
    LangChain 通过链(Chain)组件将多个调用连接在一起，创建序列化的工作流。
    Agents 可以使用工具和进行推理来做出决策和采取行动。
    Retrieval-Augmented Generation (RAG) 是一种增强 LLM 能力的方法。
    """
    
    # 创建分割器：将长文本分成较小的块
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,      # 每个块的字符数
        chunk_overlap=20     # 块之间的重叠字符数
    )
    
    # 分割文本
    chunks = text_splitter.split_text(sample_text)
    
    # 转换为 Document 对象
    from langchain_core.documents import Document
    documents = [Document(page_content=chunk) for chunk in chunks]
    
    return documents


# 步骤 2: 创建嵌入模型和 FAISS 向量存储
def create_faiss_vectorstore(documents):
    # 初始化嵌入模型
    embeddings = DashScopeEmbeddings(model="text-embedding-v2",
                                     dashscope_api_key=API_KEY)
    
    # 直接使用 from_documents 方法创建 FAISS 向量存储
    # 这是最简单且正确的方法
    vector_store = FAISS.from_documents(
        documents=documents,
        embedding=embeddings
    )
    
    return vector_store


# 步骤 3: 创建检索器
def create_retriever(vector_store):
    # 将向量存储转换为检索器
    retriever = vector_store.as_retriever(
        search_type="similarity",  # 相似度搜索
        search_kwargs={"k": 2}     # 返回前 2 个最相似的文档
    )
    return retriever


# 步骤 4: 创建 RAG 链（完全基于你的示例）
def create_rag_chain(retriever):
    # 定义提示模板
    chat_prompt = ChatPromptTemplate.from_template("""
    使用以下检索到的上下文来回答问题。
    
    上下文:
    {context}
    
    问题: {question}
    
    回答:""")
    

    # 创建通义千问模型实例
    llm = ChatTongyi(
        model_name="qwen-max",  # qwen3-max 已下线，改用稳定别名 qwen-max
        dashscope_api_key=API_KEY
    )
    
    # 构建 RAG 链：检索 & 传递问题 | 提示 | LLM | 输出解析
    retrieval_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | chat_prompt
        | llm
        | StrOutputParser()
    )
    
    return retrieval_chain


# 步骤 5: 执行 RAG 查询
def main():
    # 加载并分割文档
    print("正在加载和分割文档...")
    documents = load_and_split_documents()
    print(f"文档已分割成 {len(documents)} 个块")
    
    # 创建 FAISS 向量存储
    print("正在创建 FAISS 向量存储...")
    vector_store = create_faiss_vectorstore(documents)
    print("向量存储已创建")
    
    # 创建检索器
    retriever = create_retriever(vector_store)
    
    # 创建 RAG 链
    print("正在创建 RAG 链...")
    retrieval_chain = create_rag_chain(retriever)
    
    # 执行查询
    query = "LangChain 是什么？"
    print(f"\n查询: {query}")
    print("-" * 50)
    
    result = retrieval_chain.invoke(query)
    print(f"回答:\n{result}")
    
    # 更多查询示例
    queries = [
        "什么是 Agents？",
        "RAG 是什么意思？"
    ]
    
    for q in queries:
        print(f"\n查询: {q}")
        print("-" * 50)
        result = retrieval_chain.invoke(q)
        print(f"回答:\n{result}")


if __name__ == "__main__":
    main()
