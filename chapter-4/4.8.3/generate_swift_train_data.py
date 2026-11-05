import sqlite3
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class QAPair:
    """QA对数据类"""
    id: int
    chapter: str
    question: str
    answer: str
    created_at: str
    
    @classmethod
    def from_row(cls, row: tuple) -> 'QAPair':
        """从数据库行创建QAPair对象"""
        return cls(
            id=row[0],
            chapter=row[1],
            question=row[2],
            answer=row[3],
            created_at=row[4]
        )

class DatasetConverter:
    """数据集转换器类"""
    
    def __init__(self, db_path: str):
        """
        初始化转换器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.connection = None
        
    def connect(self) -> None:
        """连接数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            logger.info(f"成功连接到数据库: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def fetch_all_qa_pairs(self) -> List[QAPair]:
        """从数据库获取所有QA对"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("SELECT id, chapter, question, answer, created_at FROM qa_pairs")
            rows = cursor.fetchall()
            
            qa_pairs = [QAPair.from_row(row) for row in rows]
            logger.info(f"成功读取 {len(qa_pairs)} 条QA对记录")
            
            return qa_pairs
            
        except sqlite3.Error as e:
            logger.error(f"查询数据失败: {e}")
            raise
        finally:
            cursor.close()
    
    def convert_to_swift_format(self, qa_pairs: List[QAPair]) -> List[Dict[str, Any]]:
        """
        转换为阿里Swift训练工具格式
        
        Swift格式通常要求:
        {
            "conversations": [
                {"role": "human", "content": "问题内容"},
                {"role": "bot", "content": "回答内容"}
            ]
        }
        
        或者:
        {
            "instruction": "指令",
            "input": "输入",
            "output": "输出"
        }
        """
        swift_data = []
        
        for qa in qa_pairs:
            # 格式1: 对话格式 (推荐用于问答数据)
            conversation_format = {
                "conversations": [
                    {
                        "role": "user",
                        "content": qa.question
                    },
                    {
                        "role": "assistant",
                        "content": qa.answer
                    }
                ],
                "source": "neijing_qa",
                "chapter": qa.chapter,
                "id": qa.id,
                "created_at": qa.created_at
            }
            
            # 格式2: 指令格式 (备选)
            instruction_format = {
                "instruction": f"请根据《内经》知识回答以下问题（来自章节：{qa.chapter}）",
                "input": qa.question,
                "output": qa.answer,
                "chapter": qa.chapter,
                "id": qa.id,
                "created_at": qa.created_at
            }
            
            swift_data.append(conversation_format)  # 使用对话格式
        
        logger.info(f"成功转换 {len(swift_data)} 条数据为Swift格式")
        return swift_data
    
    def save_as_jsonl(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """保存为JSONL格式文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in data:
                    json_line = json.dumps(item, ensure_ascii=False)
                    f.write(json_line + '\n')
            
            logger.info(f"数据已保存到: {output_path}")
            logger.info(f"文件格式: JSONL，包含 {len(data)} 行")
            
        except IOError as e:
            logger.error(f"保存文件失败: {e}")
            raise
    
    def save_as_json(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """保存为JSON格式文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已保存到: {output_path}")
            logger.info(f"文件格式: JSON，包含 {len(data)} 条记录")
            
        except IOError as e:
            logger.error(f"保存文件失败: {e}")
            raise
    
    def save_as_csv(self, qa_pairs: List[QAPair], output_path: str) -> None:
        """保存为CSV格式文件（备选格式）"""
        try:
            import csv
            
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(['id', 'chapter', 'question', 'answer', 'created_at'])
                
                # 写入数据
                for qa in qa_pairs:
                    writer.writerow([
                        qa.id,
                        qa.chapter,
                        qa.question,
                        qa.answer,
                        qa.created_at
                    ])
            
            logger.info(f"数据已保存到: {output_path}")
            logger.info(f"文件格式: CSV，包含 {len(qa_pairs)} 条记录")
            
        except ImportError:
            logger.error("需要安装csv模块")
            raise
        except IOError as e:
            logger.error(f"保存CSV文件失败: {e}")
            raise
    
    def generate_dataset(self, output_format: str = 'jsonl', output_path: str = None) -> None:
        """
        生成数据集主方法
        
        Args:
            output_format: 输出格式，支持 'jsonl', 'json', 'csv'
            output_path: 输出文件路径，如果为None则自动生成
        """
        try:
            # 1. 连接数据库
            self.connect()
            
            # 2. 获取数据
            qa_pairs = self.fetch_all_qa_pairs()
            
            if not qa_pairs:
                logger.warning("数据库中没有找到QA对记录")
                return
            
            # 3. 生成输出文件名
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if output_format == 'jsonl':
                    output_path = f"neijing_swift_dataset_{timestamp}.jsonl"
                elif output_format == 'json':
                    output_path = f"neijing_swift_dataset_{timestamp}.json"
                elif output_format == 'csv':
                    output_path = f"neijing_qa_pairs_{timestamp}.csv"
                else:
                    raise ValueError(f"不支持的输出格式: {output_format}")
            
            # 4. 根据格式保存数据
            if output_format == 'jsonl':
                swift_data = self.convert_to_swift_format(qa_pairs)
                self.save_as_jsonl(swift_data, output_path)
            elif output_format == 'json':
                swift_data = self.convert_to_swift_format(qa_pairs)
                self.save_as_json(swift_data, output_path)
            elif output_format == 'csv':
                self.save_as_csv(qa_pairs, output_path)
            else:
                raise ValueError(f"不支持的输出格式: {output_format}")
            
            # 5. 输出统计信息
            self.print_statistics(qa_pairs)
            
        finally:
            # 6. 断开数据库连接
            self.disconnect()
    
    def print_statistics(self, qa_pairs: List[QAPair]) -> None:
        """打印数据统计信息"""
        logger.info("\n" + "="*50)
        logger.info("数据集统计信息:")
        logger.info(f"总QA对数量: {len(qa_pairs)}")
        
        # 按章节统计
        chapter_stats = {}
        for qa in qa_pairs:
            chapter_stats[qa.chapter] = chapter_stats.get(qa.chapter, 0) + 1
        
        logger.info("\n按章节分布:")
        for chapter, count in chapter_stats.items():
            logger.info(f"  {chapter}: {count} 条")
        
        # 计算平均长度
        total_question_len = sum(len(qa.question) for qa in qa_pairs)
        total_answer_len = sum(len(qa.answer) for qa in qa_pairs)
        
        if qa_pairs:
            avg_question_len = total_question_len / len(qa_pairs)
            avg_answer_len = total_answer_len / len(qa_pairs)
            logger.info(f"\n平均问题长度: {avg_question_len:.1f} 字符")
            logger.info(f"平均回答长度: {avg_answer_len:.1f} 字符")
        logger.info("="*50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='转换《内经》QA数据库为阿里Swift训练数据集')
    parser.add_argument('--db', type=str, default='neijing_qa.db',
                       help='SQLite数据库文件路径 (默认: neijing_qa.db)')
    parser.add_argument('--format', type=str, choices=['jsonl', 'json', 'csv'], default='jsonl',
                       help='输出格式 (默认: jsonl)')
    parser.add_argument('--output', type=str, help='输出文件路径 (默认自动生成)')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别 (默认: INFO)')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logger.setLevel(getattr(logging, args.log_level))
    
    try:
        # 创建转换器并生成数据集
        converter = DatasetConverter(args.db)
        converter.generate_dataset(
            output_format=args.format,
            output_path=args.output
        )
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return 1
    
    return 0


# 示例使用
def example_usage():
    """示例使用方法"""
    print("="*60)
    print("示例1: 使用默认参数")
    print("  python neijing_to_swift.py")
    print("\n示例2: 指定数据库和输出格式")
    print("  python neijing_to_swift.py --db path/to/neijing_qa.db --format json")
    print("\n示例3: 指定输出文件")
    print("  python neijing_to_swift.py --output my_dataset.jsonl")
    print("\n示例4: 获取帮助")
    print("  python neijing_to_swift.py --help")
    print("="*60)


if __name__ == "__main__":
    # 显示示例使用方法
    example_usage()
    print("\n")
    
    # 运行主程序（使用示例参数）
    import sys
    sys.argv = ['generate_swift_train_data.py', '--db', './neijing_qa_extractor/neijing_qa.db']
    main()

