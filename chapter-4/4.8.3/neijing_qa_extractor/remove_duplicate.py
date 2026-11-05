import sqlite3
from typing import List, Tuple, Dict, Any

class DuplicateQuestionChecker:
    """检查和处理重复问题的类"""
    
    def __init__(self, db_path: str):
        """初始化数据库连接"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.original_count = 0
        self.duplicate_count = 0
        self.no_duplicate_count = 0
        
    def connect(self) -> None:
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"已连接到数据库: {self.db_path}")
        
    def disconnect(self) -> None:
        """断开数据库连接"""
        if self.conn:
            self.conn.close()
            print("数据库连接已关闭")
            
    def create_tables(self) -> None:
        """创建必要的表"""
        # 创建重复记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS qa_pairs_duplicate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                original_id INTEGER,
                duplicate_reason TEXT
            )
        ''')
        
        # 创建无重复记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS qa_pairs_no_duplicate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                original_id INTEGER
            )
        ''')
        
        # 清空两个表（如果已存在）
        self.cursor.execute("DELETE FROM qa_pairs_duplicate")
        self.cursor.execute("DELETE FROM qa_pairs_no_duplicate")
        
        self.conn.commit()
        print("已创建/清空必要的表")
        
    def get_all_records(self) -> List[Tuple]:
        """获取所有原始记录"""
        self.cursor.execute("SELECT * FROM qa_pairs ORDER BY id")
        records = self.cursor.fetchall()
        self.original_count = len(records)
        print(f"从qa_pairs表中读取了{self.original_count}条记录")
        return records
    
    def check_duplicate(self, question1: str, question2: str) -> bool:
        """检查一个问题是否完全包含在另一个问题中"""
        if not question1 or not question2:
            return False
            
        # 去除空格并转换为小写进行比较（根据需求可调整）
        q1_clean = question1.strip().lower()
        q2_clean = question2.strip().lower()
        
        # 判断是否完全包含
        return (q1_clean != q2_clean) and (q1_clean in q2_clean or q2_clean in q1_clean)
    
    def find_duplicates(self) -> Dict[int, List[int]]:
        """查找所有重复的记录"""
        records = self.get_all_records()
        duplicate_map = {}  # 存储每个记录的重复记录ID列表
        
        print("开始检查重复记录...")
        
        # 双重循环比较所有记录
        for i in range(len(records)):
            id_i, chapter_i, question_i, answer_i, created_i = records[i]
            duplicate_map[id_i] = []
            
            for j in range(len(records)):
                if i == j:  # 跳过自身比较
                    continue
                    
                id_j, chapter_j, question_j, answer_j, created_j = records[j]
                
                # 检查问题是否包含
                if self.check_duplicate(question_i, question_j):
                    duplicate_map[id_i].append(id_j)
        
        return duplicate_map
    
    def process_duplicates(self) -> None:
        """处理重复记录"""
        duplicate_map = self.find_duplicates()
        records = {record[0]: record for record in self.get_all_records()}
        
        # 用于跟踪已经处理过的记录，避免重复处理
        processed = set()
        duplicate_ids = set()
        
        print("开始处理重复记录...")
        
        # 先处理有重复的记录
        for record_id, duplicate_list in duplicate_map.items():
            if record_id in processed:
                continue
                
            if duplicate_list:  # 如果有重复记录
                # 插入到重复表
                original_record = records[record_id]
                self.cursor.execute('''
                    INSERT INTO qa_pairs_duplicate 
                    (chapter, question, answer, created_at, original_id, duplicate_reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    original_record[1],  # chapter
                    original_record[2],  # question
                    original_record[3],  # answer
                    original_record[4],  # created_at
                    original_record[0],  # original_id
                    f"与记录ID {duplicate_list} 重复"  # duplicate_reason
                ))
                
                duplicate_ids.add(record_id)
                processed.add(record_id)
                self.duplicate_count += 1
        
        # 再处理无重复的记录
        for record_id, record in records.items():
            if record_id in processed:
                continue
                
            # 插入到无重复表
            self.cursor.execute('''
                INSERT INTO qa_pairs_no_duplicate 
                (chapter, question, answer, created_at, original_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                record[1],  # chapter
                record[2],  # question
                record[3],  # answer
                record[4],  # created_at
                record[0]   # original_id
            ))
            
            processed.add(record_id)
            self.no_duplicate_count += 1
        
        self.conn.commit()
        print("记录处理完成")
    
    def get_table_counts(self) -> Dict[str, int]:
        """获取各个表的数据量"""
        counts = {}
        
        # 原始表数量
        self.cursor.execute("SELECT COUNT(*) FROM qa_pairs")
        counts['original'] = self.cursor.fetchone()[0]
        
        # 重复表数量
        self.cursor.execute("SELECT COUNT(*) FROM qa_pairs_duplicate")
        counts['duplicate'] = self.cursor.fetchone()[0]
        
        # 无重复表数量
        self.cursor.execute("SELECT COUNT(*) FROM qa_pairs_no_duplicate")
        counts['no_duplicate'] = self.cursor.fetchone()[0]
        
        return counts
    
    def print_summary(self) -> None:
        """打印处理结果的摘要"""
        counts = self.get_table_counts()
        
        print("\n" + "="*60)
        print("处理结果摘要")
        print("="*60)
        print(f"原始表 (qa_pairs) 记录数量: {counts['original']}")
        print(f"重复表 (qa_pairs_duplicate) 记录数量: {counts['duplicate']}")
        print(f"无重复表 (qa_pairs_no_duplicate) 记录数量: {counts['no_duplicate']}")
        print("-"*60)
        
        # 验证数据一致性
        total_processed = counts['duplicate'] + counts['no_duplicate']
        is_consistent = (total_processed == counts['original'])
        
        print(f"重复表 + 无重复表 = {total_processed}")
        print(f"与原始表数量一致: {'是' if is_consistent else '否'}")
        
        if not is_consistent:
            print(f"警告: 数据不一致! 差异: {abs(counts['original'] - total_processed)} 条记录")
        
        # 重复率统计
        if counts['original'] > 0:
            duplicate_rate = (counts['duplicate'] / counts['original']) * 100
            print(f"重复率: {duplicate_rate:.2f}%")
        print("="*60)
    
    def run(self) -> None:
        """运行完整的检查和处理流程"""
        try:
            self.connect()
            self.create_tables()
            self.process_duplicates()
            self.print_summary()
        except Exception as e:
            print(f"处理过程中发生错误: {e}")
            if self.conn:
                self.conn.rollback()
        finally:
            self.disconnect()


# 主程序
if __name__ == "__main__":
    # 数据库文件路径
    db_path = "neijing_qa.db"
    
    # 创建检查器并运行
    checker = DuplicateQuestionChecker(db_path)
    checker.run()

