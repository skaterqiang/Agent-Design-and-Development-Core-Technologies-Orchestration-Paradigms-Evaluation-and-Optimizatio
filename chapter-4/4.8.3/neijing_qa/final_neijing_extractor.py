#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄帝内经问答对提取器 - 最终版本
功能：从huangdi_neijing.htm文件中提取问答对，并记录所属章节
作者：智能体开发实战课程
"""

import re
import html
import os
import sys
from datetime import datetime

def extract_qa_pairs_from_neijing():
    """
    从黄帝内经HTML文件中提取问答对
    返回: 问答对列表
    """
    print("=" * 60)
    print("黄帝内经问答对提取程序")
    print("=" * 60)
    print(f"[INFO] 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 读取HTML文件
    file_path = 'huangdi_neijing.htm'
    print(f"[STEP 1/5] 读取文件: {file_path}")
    
    if not os.path.exists(file_path):
        error_msg = f"[ERROR] 找不到文件: {file_path}"
        print(error_msg)
        with open('error_report.txt', 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"[SUCCESS] 文件读取成功，大小: {len(content)} 字符")
    except Exception as e:
        error_msg = f"[ERROR] 文件读取失败: {str(e)}"
        print(error_msg)
        with open('error_report.txt', 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return []
    
    # 2. 提取章节信息
    print("[STEP 2/5] 提取章节标题")
    h1_pattern = r'<h1[^>]*>(.*?)</h1>'
    raw_chapters = re.findall(h1_pattern, content, re.IGNORECASE | re.DOTALL)
    
    chapters = []
    for chapter_html in raw_chapters:
        # 清理HTML标签和实体
        cleaned = html.unescape(re.sub(r'<[^>]+>', '', chapter_html)).strip()
        if cleaned and len(cleaned) > 2:  # 过滤掉太短的章节名
            chapters.append(cleaned)
    
    print(f"[SUCCESS] 找到 {len(chapters)} 个有效章节")
    for i, chapter in enumerate(chapters[:10]):  # 显示前10个
        print(f"  {i+1:2d}. {chapter}")
    if len(chapters) > 10:
        print(f"  ... 还有 {len(chapters)-10} 个章节")
    
    # 3. 按章节分割内容并提取问答对
    print("[STEP 3/5] 按章节分割并提取问答对")
    
    # 使用<h1>标签分割内容
    sections = re.split(r'(<h1[^>]*>.*?</h1>)', content)
    
    qa_pairs = []
    current_chapter = "未知章节"
    
    print(f"[INFO] 处理 {len(sections)} 个内容段落")
    
    for i, section in enumerate(sections):
        # 检查是否是章节标题
        if re.match(r'<h1[^>]*>.*?</h1>', section):
            chapter_title = html.unescape(re.sub(r'<[^>]+>', '', section)).strip()
            if chapter_title in chapters:
                current_chapter = chapter_title
                print(f"[INFO] 当前章节: {current_chapter}")
            continue
        
        # 在当前章节中查找问答对
        # 主要模式: 帝曰/黄帝曰 ... 岐伯曰 ...
        main_pattern = r'(?:帝曰|黄帝曰)[：:]\s*([^：:岐]+?)\s*岐伯曰[：:]\s*([^<\n]+?)(?=\s*(?:帝曰|黄帝曰|岐伯曰|<h1|\Z))'
        matches = re.findall(main_pattern, section, re.DOTALL)
        
        for question, answer in matches:
            # 文本清理
            question_clean = html.unescape(question.strip())
            answer_clean = html.unescape(answer.strip())
            
            # 移除多余空白字符
            question_clean = re.sub(r'\s+', ' ', question_clean)
            answer_clean = re.sub(r'\s+', ' ', answer_clean)
            
            # 基本有效性检查
            if (len(question_clean) > 5 and len(answer_clean) > 5 and
                not re.match(r'^\s*[，。！？；：]*\s*$', question_clean) and
                not re.match(r'^\s*[，。！？；：]*\s*$', answer_clean)):
                
                qa_pairs.append({
                    'chapter': current_chapter,
                    'question': question_clean,
                    'answer': answer_clean,
                    'full_text': f"{question_clean} 岐伯曰：{answer_clean}"
                })
    
    print(f"[SUCCESS] 初步提取到 {len(qa_pairs)} 个问答对")
    
    # 4. 数据清洗和验证
    print("[STEP 4/5] 数据清洗和验证")
    
    # 去重处理
    unique_pairs = []
    seen_pairs = set()
    
    for pair in qa_pairs:
        pair_key = (pair['question'], pair['answer'])
        if pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            unique_pairs.append(pair)
    
    print(f"[INFO] 去重后剩余 {len(unique_pairs)} 个问答对")
    
    # 5. 生成结果报告
    print("[STEP 5/5] 生成结果报告")
    
    # 章节统计
    chapter_stats = {}
    for pair in unique_pairs:
        chapter = pair['chapter']
        chapter_stats[chapter] = chapter_stats.get(chapter, 0) + 1
    
    # 保存详细结果
    result_file = 'neijing_qa_detailed_results.txt'
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("黄帝内经问答对提取结果报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"源文件: {file_path}\n")
            f.write(f"总问答对数: {len(unique_pairs)}\n")
            f.write(f"涉及章节数: {len(chapter_stats)}\n")
            f.write("\n")
            
            # 章节统计
            f.write("章节分布统计:\n")
            f.write("-" * 30 + "\n")
            for chapter, count in sorted(chapter_stats.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{chapter}: {count} 个问答对\n")
            f.write("\n")
            
            # 详细问答对列表
            f.write("详细问答对列表:\n")
            f.write("=" * 60 + "\n")
            for i, pair in enumerate(unique_pairs, 1):
                f.write(f"\n第 {i} 个问答对:\n")
                f.write(f"章节: {pair['chapter']}\n")
                f.write(f"问题: {pair['question']}\n")
                f.write(f"回答: {pair['answer']}\n")
                f.write("-" * 50 + "\n")
        
        print(f"[SUCCESS] 详细结果已保存到: {result_file}")
        
    except Exception as e:
        error_msg = f"[ERROR] 保存详细结果失败: {str(e)}"
        print(error_msg)
        with open('save_error.txt', 'w', encoding='utf-8') as f:
            f.write(error_msg)
    
    # 保存JSON格式结果
    try:
        import json
        json_result = {
            "metadata": {
                "generated_time": datetime.now().isoformat(),
                "source_file": file_path,
                "total_qa_pairs": len(unique_pairs),
                "total_chapters": len(chapter_stats)
            },
            "chapter_statistics": chapter_stats,
            "qa_pairs": unique_pairs
        }
        
        with open('neijing_qa_results.json', 'w', encoding='utf-8') as f:
            json.dump(json_result, f, ensure_ascii=False, indent=2)
        
        print("[SUCCESS] JSON格式结果已保存到: neijing_qa_results.json")
        
    except Exception as e:
        print(f"[WARN] JSON格式保存失败: {str(e)}")
    
    # 显示样本结果
    print("\n" + "=" * 60)
    print("样本结果预览:")
    print("=" * 60)
    sample_count = min(3, len(unique_pairs))
    for i in range(sample_count):
        pair = unique_pairs[i]
        print(f"\n样本 {i+1}:")
        print(f"章节: {pair['chapter']}")
        print(f"问题: {pair['question']}")
        print(f"回答: {pair['answer']}")
    
    if len(unique_pairs) > sample_count:
        print(f"\n... 还有 {len(unique_pairs) - sample_count} 个问答对")
    
    print("\n" + "=" * 60)
    print("提取完成!")
    print("=" * 60)
    
    return unique_pairs

def main():
    """主函数"""
    try:
        qa_pairs = extract_qa_pairs_from_neijing()
        print(f"\n[FINAL] 成功提取 {len(qa_pairs)} 个问答对")
        return qa_pairs
    except Exception as e:
        error_msg = f"程序执行出错: {str(e)}"
        print(f"[FATAL] {error_msg}")
        with open('fatal_error.txt', 'w', encoding='utf-8') as f:
            f.write(error_msg)
            import traceback
            traceback.print_exc(file=f)
        return []

if __name__ == "__main__":
    qa_pairs = main()