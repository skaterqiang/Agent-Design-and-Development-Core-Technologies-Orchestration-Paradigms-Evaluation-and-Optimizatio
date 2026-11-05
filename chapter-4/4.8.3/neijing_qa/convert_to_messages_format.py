#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将黄帝内经问答对转换为ms-swift要求的messages格式训练数据
格式: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
"""

import json
import os
from typing import List, Dict, Any
from datetime import datetime

class MessagesFormatConverter:
    """Messages格式训练数据转换器"""
    
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.data = None
        self.system_prompt = "你是一位精通黄帝内经的中医，在回答有关皇帝内经的问题时，请务必遵循循序渐进的原则：先在内部梳理关键信息和可能的风险点（思考过程），再给出专业建议。"
        self.load_data()
    
    def load_data(self):
        """加载JSON数据"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"[INFO] 成功加载数据，共 {self.data['metadata']['total_qa_pairs']} 个问答对")
        except Exception as e:
            raise Exception(f"加载数据失败: {e}")
    
    def to_messages_format(self) -> List[Dict[str, Any]]:
        """
        转换为messages格式
        格式: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        """
        messages_data = []
        
        for pair in self.data['qa_pairs']:
            # 构造messages结构
            messages = {
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user", 
                        "content": pair['question']
                    },
                    {
                        "role": "assistant",
                        "content": pair['answer']
                    }
                ]
            }
            
            messages_data.append(messages)
        
        return messages_data
    
    def to_messages_with_chapter_format(self) -> List[Dict[str, Any]]:
        """
        转换为带章节信息的messages格式
        在system prompt中加入章节信息
        """
        messages_data = []
        
        for pair in self.data['qa_pairs']:
            # 在system prompt中加入章节信息
            enhanced_system_prompt = f"{self.system_prompt}本问题来自《黄帝内经》{pair['chapter']}。"
            
            messages = {
                "messages": [
                    {
                        "role": "system",
                        "content": enhanced_system_prompt
                    },
                    {
                        "role": "user",
                        "content": pair['question']
                    },
                    {
                        "role": "assistant", 
                        "content": pair['answer']
                    }
                ]
            }
            
            messages_data.append(messages)
        
        return messages_data
    
    def save_data(self, data: List[Dict], output_file: str):
        """保存数据到文件（每行一个JSON对象）"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in data:
                    json.dump(item, f, ensure_ascii=False)
                    f.write('\n')  # 每个JSON对象占一行
            
            print(f"[SUCCESS] Messages格式数据已保存到: {output_file}")
            print(f"[INFO] 数据条数: {len(data)}")
            
        except Exception as e:
            raise Exception(f"保存数据失败: {e}")
    
    def save_as_json_array(self, data: List[Dict], output_file: str):
        """保存为JSON数组格式"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[SUCCESS] JSON数组格式数据已保存到: {output_file}")
            print(f"[INFO] 数据条数: {len(data)}")
            
        except Exception as e:
            raise Exception(f"保存数据失败: {e}")
    
    def convert_and_save(self, output_dir: str = "."):
        """执行转换并保存所有格式"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建输出目录
        if output_dir != ".":
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 基础messages格式
            messages_data = self.to_messages_format()
            output_file1 = os.path.join(output_dir, f"neijing_qa_messages_{timestamp}.jsonl")
            self.save_data(messages_data, output_file1)
            
            # JSON数组格式（便于查看）
            output_file2 = os.path.join(output_dir, f"neijing_qa_messages_array_{timestamp}.json")
            self.save_as_json_array(messages_data, output_file2)
            
            # 带章节信息的messages格式
            messages_with_chapter_data = self.to_messages_with_chapter_format()
            output_file3 = os.path.join(output_dir, f"neijing_qa_messages_with_chapter_{timestamp}.jsonl")
            self.save_data(messages_with_chapter_data, output_file3)
            
            # 生成数据统计报告
            self.generate_report(output_dir, timestamp, len(messages_data))
            
        except Exception as e:
            print(f"[ERROR] 转换过程中发生错误: {e}")
            raise
    
    def generate_report(self, output_dir: str, timestamp: str, data_count: int):
        """生成转换报告"""
        report = {
            "conversion_info": {
                "source_file": self.input_file,
                "conversion_time": datetime.now().isoformat(),
                "total_qa_pairs": data_count,
                "total_chapters": self.data['metadata']['total_chapters'],
                "system_prompt": self.system_prompt
            },
            "chapter_distribution": self.data['chapter_statistics'],
            "generated_files": [
                f"neijing_qa_messages_{timestamp}.jsonl",
                f"neijing_qa_messages_array_{timestamp}.json", 
                f"neijing_qa_messages_with_chapter_{timestamp}.jsonl"
            ],
            "format_spec": {
                "type": "messages",
                "structure": {
                    "messages": [
                        {"role": "system", "content": "系统提示词"},
                        {"role": "user", "content": "用户问题"},
                        {"role": "assistant", "content": "助手回答"}
                    ]
                }
            }
        }
        
        report_file = os.path.join(output_dir, f"messages_conversion_report_{timestamp}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"[SUCCESS] 转换报告已保存到: {report_file}")
        
        # 打印统计信息
        print("\n" + "="*60)
        print("Messages格式转换统计报告")
        print("="*60)
        print(f"源文件: {self.input_file}")
        print(f"转换时间: {report['conversion_info']['conversion_time']}")
        print(f"总问答对数: {data_count}")
        print(f"涉及章节数: {report['conversion_info']['total_chapters']}")
        print("\n章节分布:")
        for chapter, count in report['chapter_distribution'].items():
            print(f"  {chapter}: {count} 个问答对")
        print(f"\n生成文件:")
        for file in report['generated_files']:
            print(f"  - {file}")
        print("="*60)

def main():
    """主函数"""
    print("="*60)
    print("黄帝内经问答对Messages格式转换器")
    print("="*60)
    
    # 输入文件路径
    input_file = "neijing_qa_results.json"
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"[ERROR] 找不到输入文件: {input_file}")
        return
    
    try:
        # 创建转换器实例
        converter = MessagesFormatConverter(input_file)
        
        # 执行转换
        converter.convert_and_save()
        
        print("\n[SUCCESS] Messages格式转换完成！")
        
    except Exception as e:
        print(f"[ERROR] 转换过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()