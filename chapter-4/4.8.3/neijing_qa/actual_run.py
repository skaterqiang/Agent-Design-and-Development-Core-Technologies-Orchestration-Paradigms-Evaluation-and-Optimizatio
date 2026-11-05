#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import html

def extract_qa_pairs():
    """简单提取黄帝内经中的问答对"""
    with open('huangdi_neijing.htm', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 提取章节
    chapters = re.findall(r'<h1[^>]*>(.*?)</h1>', content)
    chapters = [html.unescape(chapter.strip()) for chapter in chapters]
    
    # 按章节分割内容
    sections = re.split(r'<h1[^>]*>.*?</h1>', content)
    
    results = []
    
    # 遍历每个章节内容
    for i, section in enumerate(sections[1:], start=0):
        if i < len(chapters):
            chapter = chapters[i]
            
            # 寻找帝曰/黄帝曰 和 岐伯曰的模式
            # 更灵活的模式匹配
            pattern = r'(?:帝曰|黄帝曰)[：:]([^{<\n\r}]*?)岐伯曰[：:]([^{<\n\r}]*?)(?=<h1|</body>|<table|<pre|<xmp|<br|$)'
            matches = re.findall(pattern, section, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                question = match[0].strip()
                answer = match[1].strip()
                
                # 清理HTML标签
                question = re.sub(r'<[^>]+>', ' ', question).strip()
                answer = re.sub(r'<[^>]+>', ' ', answer).strip()
                
                # 解码HTML实体
                question = html.unescape(question)
                answer = html.unescape(answer)
                
                if len(question) > 5 and len(answer) > 5:
                    # 检查是否已存在
                    exists = False
                    for res in results:
                        if (res['question'].strip() == question.strip() and 
                            res['answer'].strip() == answer.strip()):
                            exists = True
                            break
                    
                    if not exists:
                        results.append({
                            'chapter': chapter,
                            'question': question,
                            'answer': answer
                        })
    
    return results

def main():
    print("开始提取黄帝内经问答对...")
    qa_pairs = extract_qa_pairs()
    
    print(f"共提取到 {len(qa_pairs)} 个问答对")
    print("="*80)
    
    for i, pair in enumerate(qa_pairs, 1):
        print(f"第 {i} 个问答对:")
        print(f"章节: {pair['chapter']}")
        print(f"问题: {pair['question']}")
        print(f"回答: {pair['answer']}")
        print("-" * 80)
    
    # 保存结果到文件
    with open('neijing_qa_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"黄帝内经问答对提取结果\n")
        f.write(f"总共找到 {len(qa_pairs)} 个问答对\n")
        f.write("="*80 + "\n")
        
        for i, pair in enumerate(qa_pairs, 1):
            f.write(f"第 {i} 个问答对:\n")
            f.write(f"章节: {pair['chapter']}\n")
            f.write(f"问题: {pair['question']}\n")
            f.write(f"回答: {pair['answer']}\n")
            f.write("-" * 80 + "\n")
    
    print(f"结果已保存到 neijing_qa_results.txt 文件中")

if __name__ == "__main__":
    main()