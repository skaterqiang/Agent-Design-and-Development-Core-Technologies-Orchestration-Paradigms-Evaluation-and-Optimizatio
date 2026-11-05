import sqlite3
import re

def create_database():
    """创建SQLite数据库和表"""
    conn = sqlite3.connect('neijing_qa.db')
    cursor = conn.cursor()
    
    # 创建问答对表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qa_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引以提高查询效率
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chapter ON qa_pairs(chapter)')
    
    conn.commit()
    return conn

def extract_qa_from_text(text):
    """从文本中提取问答对，改进算法"""
    # 支持跨多行的问答对提取
    # 首先定义基本的问答模式
    basic_patterns = [
        r'(黄帝问曰：.*?)(岐伯对曰：.*?)(?=\s*(?:黄帝|帝|岐伯|雷公|伯高)\s*曰：|<h1|\Z)',
        r'(黄帝曰：.*?)(岐伯[曰对]：.*?)(?=\s*(?:黄帝|帝|岐伯|雷公|伯高)\s*曰：|<h1|\Z)',
        r'(帝曰：.*?)(岐伯[曰对]：.*?)(?=\s*(?:黄帝|帝|岐伯|雷公|伯高)\s*曰：|<h1|\Z)',
        r'(岐伯[曰对]：.*?)(黄帝[曰问]：.*?)(?=\s*(?:黄帝|帝|岐伯|雷公|伯高)\s*曰：|<h1|\Z)',
        r'(雷公问曰：.*?)(帝曰：.*?)(?=\s*(?:黄帝|帝|岐伯|雷公|伯高)\s*曰：|<h1|\Z)',
        r'(帝曰：.*?)(雷公曰：.*?)(?=\s*(?:黄帝|帝|岐伯|雷公|伯高)\s*曰：|<h1|\Z)',
    ]
    
    qa_pairs = []
    
    for pattern in basic_patterns:
        # 使用re.DOTALL和re.MULTILINE标志
        matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
        for question, answer in matches:
            question = question.strip()
            answer = answer.strip()
            
            # 验证内容有效性
            if (len(question) > 5 and len(answer) > 5 and 
                ('曰：' in question or '问曰：' in question) and 
                ('曰：' in answer or '对曰：' in answer)):
                # 移除HTML标签并清理文本
                question_clean = re.sub(r'<[^>]+>', ' ', question)
                answer_clean = re.sub(r'<[^>]+>', ' ', answer)
                
                # 去除多余的空白字符，但保留有意义的换行和分段
                question_clean = re.sub(r'\s+', ' ', question_clean).strip()
                answer_clean = re.sub(r'\s+', ' ', answer_clean).strip()
                
                qa_pairs.append((question_clean, answer_clean))
    
    # 处理特殊情况：段落标签分隔的问答
    # 查找可能的问答对，即使它们跨越了多个段落
    extended_patterns = [
        # 处理<p>标签分隔的情况
        r'(<p>.*?)(?:\s*<p>\s*)*(.*?曰：.*?)(.*?)(?:\s*<p>\s*)*(.*?曰：.*?)(.*?)(?=<h1|\Z)',
    ]
    
    # 对于复杂的情况，我们需要使用状态机方法
    # 按行分割文本，逐行查找问答模式
    lines = text.split('\n')
    current_question = None
    current_answer = None
    in_question = False
    in_answer = False
    
    for line in lines:
        # 清理当前行
        clean_line = re.sub(r'<[^>]+>', ' ', line).strip()
        if not clean_line:
            continue
            
        # 检查是否是问题行
        if any(keyword in line for keyword in ['黄帝问曰：', '帝问曰：', '黄帝曰：', '帝曰：', '雷公问曰：']):
            # 如果已经有上一个问题，先保存
            if current_question and current_answer:
                qa_pairs.append((current_question.strip(), current_answer.strip()))
            
            # 开始新问题
            current_question = clean_line
            current_answer = None
            in_question = True
            in_answer = False
        
        # 检查是否是答案行
        elif any(keyword in line for keyword in ['岐伯对曰：', '岐伯曰：', '雷公曰：', '伯高曰：']):
            current_answer = clean_line
            in_question = False
            in_answer = True
        
        # 如果当前正在处理答案，并且行中包含下一个问题的开始，则结束当前答案
        elif current_answer and any(keyword in line for keyword in ['黄帝问曰：', '帝问曰：', '黄帝曰：', '帝曰：']):
            # 保存当前问答对
            if current_question and current_answer:
                qa_pairs.append((current_question.strip(), current_answer.strip()))
            
            # 开始新的问题
            current_question = clean_line
            current_answer = None
            in_question = True
            in_answer = False
        
        # 如果在答案过程中，继续添加到当前答案
        elif current_answer and in_answer and clean_line and not any(keyword in clean_line for keyword in ['<h1', '<h2', '<h3']):
            current_answer += ' ' + clean_line
    
    # 保存最后的问答对
    if current_question and current_answer:
        qa_pairs.append((current_question.strip(), current_answer.strip()))
    
    return qa_pairs

def main():
    # 读取HTML文件
    try:
        with open('huangdi_neijing.htm', 'r', encoding='utf-8') as file:
            html_content = file.read()
    except FileNotFoundError:
        print("错误：找不到 huangdi_neijing.htm 文件")
        return
    except UnicodeDecodeError:
        # 如果UTF-8失败，尝试其他编码
        try:
            with open('huangdi_neijing.htm', 'r', encoding='gbk') as file:
                html_content = file.read()
        except UnicodeDecodeError:
            print("错误：无法解码文件，请确认文件编码格式")
            return
    
    # 创建数据库连接
    conn = create_database()
    cursor = conn.cursor()
    
    print("正在解析HTML并提取问答对...")
    
    # 通过<h1>标签准确分割章节
    h1_pattern = r'<h1[^>]*>(.*?)</h1>'
    
    # 找到所有<h1>标签的位置
    matches = list(re.finditer(h1_pattern, html_content))
    print(f"总共找到 {len(matches)} 个<h1>标签")
    
    chapters = []
    
    for i, match in enumerate(matches):
        # 获取章节标题
        title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
        
        # 确定章节内容的开始和结束位置
        start_pos = match.end()
        
        # 确定章节内容的结束位置（下一个<h1>标签的开始或文档结尾）
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(html_content)
        
        # 提取章节内容
        content = html_content[start_pos:end_pos]
        
        chapters.append((title, content))
        print(f"章节 {i+1}: {title}")
    
    # 提取所有问答对
    total_qa_count = 0
    
    for chapter_title, chapter_content in chapters:
        qa_pairs = extract_qa_from_text(chapter_content)
        
        if qa_pairs:  # 只显示有问答对的章节
            print(f"章节 '{chapter_title[:20]}{'...' if len(chapter_title) > 20 else ''}' 提取到 {len(qa_pairs)} 个问答对")
        
        # 插入数据库
        for question, answer in qa_pairs:
            try:
                cursor.execute(
                    "INSERT INTO qa_pairs (chapter, question, answer) VALUES (?, ?, ?)",
                    (chapter_title, question, answer)
                )
                total_qa_count += 1
            except Exception as e:
                print(f"插入数据时出错: {e}")
                continue
    
    # 提交更改
    conn.commit()
    
    # 输出统计信息
    total_records = cursor.execute("SELECT COUNT(*) FROM qa_pairs").fetchone()[0]
    print(f"\n完成！总共提取了 {total_records} 个问答对")
    
    if total_records > 0:
        # 显示一些示例
        examples = cursor.execute("SELECT chapter, question, answer FROM qa_pairs LIMIT 5").fetchall()
        print("\n前5个问答对示例：")
        for i, (chap, ques, ans) in enumerate(examples, 1):
            print(f"{i}. 章节: {chap}")
            print(f"   问题: {ques[:200]}{'...' if len(ques) > 200 else ''}")
            print(f"   答案: {ans[:200]}{'...' if len(ans) > 200 else ''}")
            print()
        
        # 按章节统计
        chapter_stats = cursor.execute("""
            SELECT chapter, COUNT(*) as count 
            FROM qa_pairs 
            GROUP BY chapter 
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        print("各章节问答对数量统计（前10）：")
        for chap, cnt in chapter_stats:
            print(f"  {cnt} 个 - {chap[:50]}{'...' if len(chap) > 50 else ''}")
    
    # 关闭连接
    conn.close()
    print("\n数据已保存到 neijing_qa.db 数据库中")

if __name__ == "__main__":
    main()