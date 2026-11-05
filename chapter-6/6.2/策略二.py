# RAG知识检索模块（简化示例）
class SOPKnowledgeRetriever:
    """SOP知识检索器"""
    
    def __init__(self, vector_store, sop_documents):
        self.vector_store = vector_store
        self.sop_documents = sop_documents
        
    def retrieve_relevant_sop(self, user_query, complaint_type="damaged_goods"):
        """检索相关SOP知识"""
        # 1. 基于用户查询检索相关SOP片段
        query_embedding = self.get_embedding(user_query)
        relevant_chunks = self.vector_store.similarity_search(
            query_embedding, 
            k=3,
            filter={"type": "sop", "scenario": complaint_type}
        )
        
        # 2. 构建SOP上下文
        sop_context = self.build_sop_context(relevant_chunks)
        
        return sop_context
    
    def build_sop_context(self, chunks):
        """构建SOP上下文提示"""
        context = "## 相关SOP流程（请严格遵循）：\n\n"
        for i, chunk in enumerate(chunks, 1):
            context += f"{i}. {chunk['content']}\n"
            if 'required_keywords' in chunk:
                context += f"   必含关键词: {', '.join(chunk['required_keywords'])}\n"
            if 'mandatory_actions' in chunk:
                context += f"   必做动作: {', '.join(chunk['mandatory_actions'])}\n"
            context += "\n"
        
        return context