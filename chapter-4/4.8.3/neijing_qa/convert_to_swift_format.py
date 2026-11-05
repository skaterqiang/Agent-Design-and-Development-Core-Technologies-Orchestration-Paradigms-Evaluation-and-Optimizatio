#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将黄帝内经问答对转换为ms-swift训练数据格式
支持多种格式：Alpaca、ShareGPT、ChatML等
"""

import json
import os
from typing import List, Dict, Any
from datetime import datetime

class NeijingDataConverter:
    """黄帝内经数据格式转换器"""
    
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.data = None
        self.load_data()
    
    def load_data(self):
        """加载JSON数据"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"[INFO] 成功加载数据，共 {self.data['metadata']['total_qa_pairs']} 个问答对")
        except Exception as e:
            raise Exception(f"加载数据失败: {e}")
    
    def to_alpaca_format(self) -> List[Dict[str, str]]:
        """
        转换为Alpaca格式
        格式: {"instruction": "...", "input": "...", "output": "..."}
        """
        alpaca_data = []
        
        for pair in self.data['qa_pairs']:
            # 构造指令
            instruction = f"请根据《黄帝内经》{pair['chapter']}的内容回答以下中医问题："
            
            # 问题作为输入
            input_text = pair['question']
            
            # 答案作为输出
            output_text = pair['answer']
            
            alpaca_item = {
                "instruction": instruction,
                "input": input_text,
                "output": output_text
            }
            
            alpaca_data.append(alpaca_item)
        
        return alpaca_data
    
    def to_sharegpt_format(self) -> List[Dict[str, Any]]:
        """
        转换为ShareGPT格式
        格式: {"conversations": [{"from": "human", "value": "..."}, {"from": "gpt", "value": "..."}]}
        """
        sharegpt_data = []
        
        for pair in self.data['qa_pairs']:
            conversation = {
                "conversations": [
                    {
                        "from": "human",
                        "value": f"《黄帝内经》{pair['chapter']}中提到：{pair['question']}"
                    },
                    {
                        "from": "gpt",
                        "value": pair['answer']
                    }
                ]
            }
            sharegpt_data.append(conversation)
        
        return sharegpt_data
    
    def to_chatml_format(self) -> List[Dict[str, str]]:
        """
        转换为ChatML格式
        格式: {"prompt": "<|im_start|>system\n...\n<|im_start|>user\n...\n<|im_end|>\n<|im_start|>assistant\n", "completion": "...<|im_end|>"}
        """
        chatml_data = []
        
        system_prompt = "你是一位精通《黄帝内经》的中医专家，请根据经典内容准确回答相关问题。"
        
        for pair in self.data['qa_pairs']:
            prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            prompt += f"<|im_start|>user\n《黄帝内经》{pair['chapter']}中记载：{pair['question']}<|im_end|>\n"
            prompt += "<|im_start|>assistant\n"
            
            completion = f"{pair['answer']}<|im_end|>"
            
            chatml_item = {
                "prompt": prompt,
                "completion": completion
            }
            
            chatml_data.append(chatml_item)
        
        return chatml_data
    
    def to_instruction_format(self) -> List[Dict[str, str]]:
        """
        转换为通用指令微调格式
        格式: {"text": "Instruction: ...\nInput: ...\nOutput: ..."}
        """
        instruction_data = []
        
        for pair in self.data['qa_pairs']:
            text = f"Instruction: 作为一名中医专家，请根据《黄帝内经》{pair['chapter']}回答以下问题\n"
            text += f"Input: {pair['question']}\n"
            text += f"Output: {pair['answer']}"
            
            instruction_item = {"text": text}
            instruction_data.append(instruction_item)
        
        return instruction_data
    
    def save_data(self, data: List[Dict], output_file: str, format_type: str):
        """保存数据到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[SUCCESS] {format_type}格式数据已保存到: {output_file}")
            print(f"[INFO] 数据条数: {len(data)}")
            
        except Exception as e:
            raise Exception(f"保存数据失败: {e}")
    
    def convert_all_formats(self, output_dir: str = "."):
        """转换为所有支持的格式"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建输出目录
        if output_dir != ".":
            os.makedirs(output_dir, exist_ok=True)
        
        formats = {
            "alpaca": self.to_alpaca_format,
            "sharegpt": self.to_sharegpt_format,
            "chatml": self.to_chatml_format,
            "instruction": self.to_instruction_format
        }
        
        for format_name, converter_func in formats.items():
            try:
                converted_data = converter_func()
                output_file = os.path.join(
                    output_dir, 
                    f"neijing_qa_{format_name}_{timestamp}.json"
                )
                self.save_data(converted_data, output_file, format_name.upper())
                
            except Exception as e:
                print(f"[ERROR] 转换{format_name.upper()}格式时出错: {e}")
        
        # 生成数据统计报告
        self.generate_report(output_dir, timestamp)
    
    def generate_report(self, output_dir: str, timestamp: str):
        """生成数据转换报告"""
        report = {
            "conversion_info": {
                "source_file": self.input_file,
                "conversion_time": datetime.now().isoformat(),
                "total_qa_pairs": self.data['metadata']['total_qa_pairs'],
                "total_chapters": self.data['metadata']['total_chapters']
            },
            "chapter_distribution": self.data['chapter_statistics'],
            "generated_formats": [
                "alpaca",
                "sharegpt", 
                "chatml",
                "instruction"
            ]
        }
        
        report_file = os.path.join(output_dir, f"conversion_report_{timestamp}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"[SUCCESS] 转换报告已保存到: {report_file}")
        
        # 打印统计信息
        print("\n" + "="*60)
        print("数据转换统计报告")
        print("="*60)
        print(f"源文件: {self.input_file}")
        print(f"转换时间: {report['conversion_info']['conversion_time']}")
        print(f"总问答对数: {report['conversion_info']['total_qa_pairs']}")
        print(f"涉及章节数: {report['conversion_info']['total_chapters']}")
        print("\n章节分布:")
        for chapter, count in report['chapter_distribution'].items():
            print(f"  {chapter}: {count} 个问答对")
        print(f"\n生成格式: {', '.join(report['generated_formats'])}")
        print("="*60)

def main():
    """主函数"""
    print("="*60)
    print("黄帝内经问答对数据格式转换器")
    print("="*60)
    
    # 输入文件路径
    input_file = "neijing_qa_results.json"
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"[ERROR] 找不到输入文件: {input_file}")
        return
    
    try:
        # 创建转换器实例
        converter = NeijingDataConverter(input_file)
        
        # 执行转换
        converter.convert_all_formats()
        
        print("\n[SUCCESS] 所有格式转换完成！")
        
    except Exception as e:
        print(f"[ERROR] 转换过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()