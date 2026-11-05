"""
6.3.4 完整代码：从零开始训练GPT-2风格的代码生成模型（小数据集演示版）
说明：这是一个演示版本，使用小数据集在几分钟内完成训练演示
"""

import os
import sys
import torch
import math
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from tqdm.auto import tqdm

# ==================== 第一部分：环境设置和配置 ====================

@dataclass
class TrainingConfig:
    """训练配置类（小数据集演示版）"""
    # 模型配置（超小模型，快速训练）
    model_name: str = "mini-codeparrot-demo"
    context_length: int = 64      # 减少上下文长度，加快处理
    vocab_size: int = 50257       # GPT-2标准词汇表大小
    n_layer: int = 4              # 减少层数，降低计算量
    n_head: int = 4               # 减少注意力头数
    n_embd: int = 256             # 减少隐藏层维度
    
    # 训练配置（小批量，快速收敛）
    batch_size: int = 8           # 小批量，适合演示
    eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-3   # 稍大的学习率，加快收敛
    weight_decay: float = 0.05
    num_epochs: int = 3           # 少量epoch，演示用
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    
    # 数据配置（小数据集）
    dataset_size: int = 1000      # 总数据集大小
    train_ratio: float = 0.8      # 训练集比例
    
    # 输出配置
    output_dir: str = "./mini-codeparrot-demo"
    log_dir: str = "./logs"
    save_steps: int = 50          # 频繁保存，便于观察
    eval_steps: int = 20          # 频繁评估
    logging_steps: int = 10       # 频繁记录
    
    # 设备配置
    use_fp16: bool = False        # 演示中关闭混合精度，简化
    use_cuda: bool = torch.cuda.is_available()
    
    def __post_init__(self):
        """初始化后处理"""
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 设置设备
        self.device = torch.device("cuda" if self.use_cuda else "cpu")
        
        # 打印配置
        print("=" * 60)
        print("训练配置（小数据集演示版）:")
        print("=" * 60)
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                print(f"{key:30}: {value}")
        print("=" * 60)

# ==================== 第二部分：数据准备 ====================

class DatasetProcessor:
    """数据集处理器（小数据集演示版）"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        
    def create_tiny_dataset(self):
        """创建微型数据集（仅用于演示）"""
        print("\n" + "="*60)
        print("创建微型数据集...")
        print("="*60)
        
        # 使用Python代码片段作为训练数据
        python_code_snippets = [
            # 基础Python
            "def hello_world():\n    print('Hello, World!')\n",
            "def add_numbers(a, b):\n    return a + b\n",
            "def multiply_numbers(a, b):\n    return a * b\n",
            "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)\n",
            "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n",
            
            # 数据科学相关
            "import pandas as pd\n",
            "import numpy as np\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "from sklearn.model_selection import train_test_split\n",
            
            # 数据处理
            "df = pd.read_csv('data.csv')\n",
            "df.head()\n",
            "df.describe()\n",
            "df.isnull().sum()\n",
            "df.fillna(0, inplace=True)\n",
            
            # 数据可视化
            "plt.plot(x, y)\n",
            "plt.scatter(x, y)\n",
            "plt.hist(data, bins=20)\n",
            "plt.title('My Plot')\n",
            "plt.xlabel('X axis')\n",
            "plt.ylabel('Y axis')\n",
            
            # 机器学习
            "from sklearn.linear_model import LinearRegression\n",
            "model = LinearRegression()\n",
            "model.fit(X_train, y_train)\n",
            "predictions = model.predict(X_test)\n",
            "accuracy = model.score(X_test, y_test)\n",
            
            # 控制流
            "for i in range(10):\n    print(i)\n",
            "while condition:\n    do_something()\n",
            "if x > 0:\n    print('Positive')\nelse:\n    print('Non-positive')\n",
            
            # 列表推导式
            "squares = [x**2 for x in range(10)]\n",
            "evens = [x for x in range(20) if x % 2 == 0]\n",
            
            # 字典操作
            "my_dict = {'a': 1, 'b': 2, 'c': 3}\n",
            "for key, value in my_dict.items():\n    print(key, value)\n",
            
            # 文件操作
            "with open('file.txt', 'r') as f:\n    content = f.read()\n",
            "with open('output.txt', 'w') as f:\n    f.write('Hello')\n",
            
            # 错误处理
            "try:\n    risky_operation()\nexcept Exception as e:\n    print(f'Error: {e}')\n",
            
            # 类和对象
            "class Dog:\n    def __init__(self, name):\n        self.name = name\n    \n    def bark(self):\n        print(f'{self.name} says woof!')\n",
        ]
        
        # 扩展数据集：创建一些组合和变体
        expanded_samples = []
        for snippet in python_code_snippets:
            # 原始版本
            expanded_samples.append(snippet)
            
            # 添加注释版本
            expanded_samples.append(f"# Python代码示例\n{snippet}")
            
            # 添加导入语句
            if not snippet.startswith("import") and not snippet.startswith("from"):
                expanded_samples.append(f"import math\n{snippet}")
        
        # 确保我们有足够的数据
        total_needed = self.config.dataset_size
        current_count = len(expanded_samples)
        
        if current_count < total_needed:
            # 重复现有样本直到达到所需数量
            repeat_factor = total_needed // current_count + 1
            all_samples = expanded_samples * repeat_factor
            all_samples = all_samples[:total_needed]
        else:
            all_samples = expanded_samples[:total_needed]
        
        # 划分训练集和验证集
        train_size = int(len(all_samples) * self.config.train_ratio)
        train_samples = all_samples[:train_size]
        valid_samples = all_samples[train_size:]
        
        print(f"创建的训练集大小: {len(train_samples)}")
        print(f"创建的验证集大小: {len(valid_samples)}")
        
        # 显示一些样本
        print("\n数据集示例（前3个）:")
        for i in range(min(3, len(train_samples))):
            print(f"样本 {i+1}:")
            print(train_samples[i])
            print("-" * 40)
        
        return {
            "train": train_samples,
            "valid": valid_samples
        }

# ==================== 第三部分：分词器和模型初始化 ====================

class ModelInitializer:
    """模型初始化器"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.tokenizer = None
        self.model = None
        
    def load_tokenizer(self):
        """加载分词器"""
        print("\n" + "="*60)
        print("初始化分词器...")
        print("="*60)
        
        try:
            from transformers import AutoTokenizer
            
            # 使用GPT-2分词器（标准版）
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
            
            # 设置填充token
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # 打印分词器信息
            print(f"词汇表大小: {tokenizer.vocab_size}")
            print(f"特殊标记: {tokenizer.special_tokens_map}")
            
            # 测试分词
            test_code = "def hello_world():\n    print('Hello')"
            tokens = tokenizer.tokenize(test_code)
            print(f"测试分词 ('{test_code[:20]}...'): {tokens[:10]}...")
            
            self.tokenizer = tokenizer
            return tokenizer
            
        except ImportError as e:
            print(f"错误: 需要安装transformers库 - {e}")
            print("请运行: pip install transformers")
            sys.exit(1)
            
    def initialize_model(self, tokenizer):
        """初始化模型"""
        print("\n" + "="*60)
        print("初始化模型...")
        print("="*60)
        
        try:
            from transformers import AutoConfig, GPT2LMHeadModel
            
            # 创建模型配置
            config = AutoConfig.from_pretrained(
                "gpt2",
                vocab_size=len(tokenizer),
                n_ctx=self.config.context_length,
                bos_token_id=tokenizer.bos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                n_layer=self.config.n_layer,
                n_head=self.config.n_head,
                n_embd=self.config.n_embd
            )
            
            # 创建新模型（随机初始化）
            model = GPT2LMHeadModel(config)
            
            # 计算模型参数
            total_params = sum(p.numel() for p in model.parameters())
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            
            print(f"模型架构: 迷你GPT-2 (演示版)")
            print(f"总参数量: {total_params:,}")
            print(f"可训练参数量: {trainable_params:,}")
            print(f"Transformer层数: {self.config.n_layer}")
            print(f"注意力头数: {self.config.n_head}")
            print(f"隐藏层维度: {self.config.n_embd}")
            
            # 移动到设备
            model.to(self.config.device)
            print(f"模型已移动到: {self.config.device}")
            
            self.model = model
            return model
            
        except Exception as e:
            print(f"初始化模型时出错: {e}")
            raise

# ==================== 第四部分：数据预处理 ====================

class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self, config: TrainingConfig, tokenizer):
        self.config = config
        self.tokenizer = tokenizer
        
    def tokenize_and_prepare(self, datasets_dict):
        """对数据集进行分词处理并准备为PyTorch格式"""
        print("\n" + "="*60)
        print("处理数据集...")
        print("="*60)
        
        def tokenize_batch(texts):
            """批量分词函数"""
            # 对代码进行分词
            tokenized = self.tokenizer(
                texts,
                truncation=True,
                max_length=self.config.context_length,
                padding="max_length",  # 填充到固定长度
                return_tensors="pt"
            )
            
            return tokenized
        
        # 处理训练集
        print("处理训练集...")
        train_encodings = tokenize_batch(datasets_dict["train"])
        
        # 处理验证集
        print("处理验证集...")
        valid_encodings = tokenize_batch(datasets_dict["valid"])
        
        # 创建PyTorch数据集
        class CodeDataset(torch.utils.data.Dataset):
            def __init__(self, encodings):
                self.encodings = encodings
                
            def __getitem__(self, idx):
                item = {key: val[idx] for key, val in self.encodings.items()}
                # 因果语言建模的标签就是输入本身（模型会内部处理移位）
                item["labels"] = item["input_ids"].clone()
                return item
            
            def __len__(self):
                return len(self.encodings.input_ids)
        
        train_dataset = CodeDataset(train_encodings)
        valid_dataset = CodeDataset(valid_encodings)
        
        print(f"训练集样本数: {len(train_dataset):,}")
        print(f"验证集样本数: {len(valid_dataset):,}")
        
        # 检查一个样本
        sample = train_dataset[0]
        print(f"\n样本检查:")
        print(f"输入ID形状: {sample['input_ids'].shape}")
        print(f"注意力掩码形状: {sample['attention_mask'].shape}")
        print(f"标签形状: {sample['labels'].shape}")
        
        # 解码第一个样本查看
        decoded = self.tokenizer.decode(sample['input_ids'], skip_special_tokens=True)
        print(f"\n解码的第一个样本（前100字符）:")
        print(decoded[:100] + "...")
        
        return train_dataset, valid_dataset
    
    def create_data_collator(self):
        """创建数据整理器"""
        from transformers import DataCollatorForLanguageModeling
        
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # 使用因果语言建模
        )
        
        return data_collator

# ==================== 第五部分：训练器实现 ====================

class DemoTrainer:
    """演示用训练器（简化版）"""
    
    def __init__(self, model, config, tokenizer, train_dataset, valid_dataset):
        self.model = model
        self.config = config
        self.tokenizer = tokenizer
        self.train_dataset = train_dataset
        self.valid_dataset = valid_dataset
        
        # 训练状态
        self.global_step = 0
        self.epoch = 0
        self.best_loss = float('inf')
        
        # 训练历史
        self.history = {
            "train_loss": [],
            "valid_loss": [],
            "learning_rate": [],
            "step": [],
            "epoch": []
        }
        
        # 初始化优化器
        self.optimizer = self.create_optimizer()
        
        # 初始化学习率调度器
        self.scheduler = self.create_scheduler()
        
    def create_optimizer(self):
        """创建优化器（简化版）"""
        from torch.optim import AdamW
        
        optimizer = AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        
        return optimizer
    
    def create_scheduler(self):
        """创建学习率调度器（简化版）"""
        from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
        
        # 使用余弦退火调度器
        scheduler = CosineAnnealingWarmRestarts(
            self.optimizer,
            T_0=50,  # 初始周期
            T_mult=2  # 周期倍增因子
        )
        
        return scheduler
    
    def train_epoch(self, train_loader, epoch):
        """训练一个epoch"""
        self.model.train()
        self.epoch = epoch
        
        total_loss = 0
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{self.config.num_epochs}")
        
        for step, batch in enumerate(progress_bar):
            # 准备输入
            batch = {k: v.to(self.config.device) for k, v in batch.items()}
            
            # 前向传播
            outputs = self.model(**batch)
            loss = outputs.loss
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(), 
                self.config.max_grad_norm
            )
            
            # 优化器步骤
            self.optimizer.step()
            self.scheduler.step()
            self.optimizer.zero_grad()
            
            # 更新状态
            total_loss += loss.item()
            self.global_step += 1
            
            # 更新进度条
            avg_loss = total_loss / (step + 1)
            progress_bar.set_postfix({
                "loss": f"{avg_loss:.4f}",
                "lr": f"{self.scheduler.get_last_lr()[0]:.2e}"
            })
            
            # 记录训练历史
            if self.global_step % self.config.logging_steps == 0:
                self.history["train_loss"].append(avg_loss)
                self.history["step"].append(self.global_step)
                self.history["epoch"].append(epoch)
                self.history["learning_rate"].append(self.scheduler.get_last_lr()[0])
            
            # 定期评估
            if self.global_step % self.config.eval_steps == 0:
                valid_loss = self.evaluate()
                self.history["valid_loss"].append(valid_loss)
                
                # 保存最佳模型
                if valid_loss < self.best_loss:
                    self.best_loss = valid_loss
                    self.save_model(f"best_model_step_{self.global_step}")
            
            # 定期保存检查点
            if self.global_step % self.config.save_steps == 0:
                self.save_model(f"checkpoint_step_{self.global_step}")
        
        return total_loss / len(train_loader)
    
    def evaluate(self):
        """评估模型"""
        print("\n正在评估模型...")
        
        self.model.eval()
        total_loss = 0
        
        from torch.utils.data import DataLoader
        
        valid_loader = DataLoader(
            self.valid_dataset,
            batch_size=self.config.eval_batch_size,
            shuffle=False
        )
        
        with torch.no_grad():
            for batch in valid_loader:
                batch = {k: v.to(self.config.device) for k, v in batch.items()}
                outputs = self.model(**batch)
                total_loss += outputs.loss.item()
        
        avg_loss = total_loss / len(valid_loader)
        print(f"验证损失: {avg_loss:.4f}")
        
        self.model.train()
        return avg_loss
    
    def save_model(self, name):
        """保存模型"""
        save_path = os.path.join(self.config.output_dir, name)
        os.makedirs(save_path, exist_ok=True)
        
        # 保存模型
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
        
        # 保存训练状态
        torch.save({
            'global_step': self.global_step,
            'epoch': self.epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_loss': self.best_loss,
            'history': self.history
        }, os.path.join(save_path, 'training_state.pt'))
        
        print(f"模型已保存到: {save_path}")
    
    def plot_training_history(self):
        """绘制训练历史图表"""
        if not self.history["train_loss"]:
            print("没有训练历史可绘制")
            return
        
        plt.figure(figsize=(12, 8))
        
        # 创建2x2的子图
        # 1. 训练损失
        plt.subplot(2, 2, 1)
        plt.plot(self.history["train_loss"])
        plt.title('Training Loss')
        plt.xlabel('Log Interval')
        plt.ylabel('Loss')
        plt.grid(True)
        
        # 2. 验证损失
        plt.subplot(2, 2, 2)
        if self.history["valid_loss"]:
            plt.plot(self.history["valid_loss"])
            plt.title('Validation Loss')
            plt.xlabel('Eval Interval')
            plt.ylabel('Loss')
            plt.grid(True)
        
        # 3. 学习率
        plt.subplot(2, 2, 3)
        plt.plot(self.history["learning_rate"])
        plt.title('Learning Rate')
        plt.xlabel('Log Interval')
        plt.ylabel('LR')
        plt.grid(True)
        
        # 4. 困惑度
        plt.subplot(2, 2, 4)
        perplexities = [math.exp(loss) for loss in self.history["train_loss"]]
        plt.plot(perplexities)
        plt.title('Perplexity')
        plt.xlabel('Log Interval')
        plt.ylabel('Perplexity')
        plt.grid(True)
        
        plt.tight_layout()
        
        # 保存图表
        plot_path = os.path.join(self.config.log_dir, 'demo_training_history.png')
        plt.savefig(plot_path, dpi=150)
        print(f"训练历史图表已保存到: {plot_path}")
        
        plt.show()

# ==================== 第六部分：生成器 ====================

class CodeGenerator:
    """代码生成器"""
    
    def __init__(self, model, tokenizer, config):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        
        # 设置为评估模式
        self.model.eval()
    
    def generate(self, prompt, max_new_tokens=50, temperature=0.7, top_p=0.9):
        """生成代码"""
        # 编码提示
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.config.device)
        
        # 生成配置
        generation_config = {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "do_sample": True,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        
        # 生成代码
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                **generation_config
            )
        
        # 解码生成的代码
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return generated_text
    
    def demo_generation(self):
        """演示生成功能"""
        print("\n" + "="*60)
        print("代码生成演示")
        print("="*60)
        
        test_prompts = [
            "def hello_world():",
            "import pandas as pd\n# 读取CSV文件",
            "import matplotlib.pyplot as plt\n# 绘制正弦波",
            "# 使用循环打印数字",
            "class Animal:\n    def __init__(self, name):"
        ]
        
        results = []
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n演示 {i}:")
            print(f"提示:\n{prompt}\n")
            
            generated = self.generate(prompt, max_new_tokens=30)
            print(f"生成代码:\n{generated}\n")
            print("-" * 60)
            
            results.append({
                "prompt": prompt,
                "generated": generated
            })
        
        return results

# ==================== 第七部分：主训练流程 ====================

class DemoTrainingPipeline:
    """演示用训练流程（简化版）"""
    
    def __init__(self):
        self.config = TrainingConfig()
        
    def run(self):
        """运行完整训练流程"""
        print("\n" + "="*60)
        print("开始迷你GPT-2代码生成模型演示训练")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            # 步骤1: 数据准备
            print("\n[步骤1/4] 数据准备")
            data_processor = DatasetProcessor(self.config)
            datasets_dict = data_processor.create_tiny_dataset()
            
            # 步骤2: 初始化分词器和模型
            print("\n[步骤2/4] 初始化模型")
            model_initializer = ModelInitializer(self.config)
            tokenizer = model_initializer.load_tokenizer()
            model = model_initializer.initialize_model(tokenizer)
            
            # 步骤3: 数据预处理
            print("\n[步骤3/4] 数据预处理")
            data_preprocessor = DataPreprocessor(self.config, tokenizer)
            train_dataset, valid_dataset = data_preprocessor.tokenize_and_prepare(datasets_dict)
            
            # 创建数据加载器
            from torch.utils.data import DataLoader
            
            train_loader = DataLoader(
                train_dataset,
                batch_size=self.config.batch_size,
                shuffle=True
            )
            
            # 步骤4: 训练
            print("\n[步骤4/4] 训练模型")
            trainer = DemoTrainer(
                model, 
                self.config, 
                tokenizer,
                train_dataset,
                valid_dataset
            )
            
            # 开始训练
            for epoch in range(self.config.num_epochs):
                print(f"\n开始第 {epoch+1}/{self.config.num_epochs} 轮训练")
                avg_loss = trainer.train_epoch(train_loader, epoch)
                print(f"第 {epoch+1} 轮平均损失: {avg_loss:.4f}")
            
            # 保存最终模型
            trainer.save_model("final_demo_model")
            
            # 绘制训练历史
            trainer.plot_training_history()
            
            # 演示生成
            print("\n[额外演示] 代码生成测试")
            generator = CodeGenerator(model, tokenizer, self.config)
            generation_results = generator.demo_generation()
            
            # 保存生成结果
            self.save_results(generation_results)
            
            # 计算总时间
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("\n" + "="*60)
            print(f"演示训练完成! 总用时: {duration:.1f} 秒")
            print("="*60)
            
        except Exception as e:
            print(f"\n训练过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
    
    def save_results(self, generation_results):
        """保存结果"""
        results_path = os.path.join(self.config.output_dir, "demo_generation_results.txt")
        
        with open(results_path, "w", encoding="utf-8") as f:
            f.write("代码生成演示结果\n")
            f.write("=" * 60 + "\n\n")
            
            for i, result in enumerate(generation_results, 1):
                f.write(f"演示 {i}:\n")
                f.write(f"提示:\n{result['prompt']}\n")
                f.write(f"生成代码:\n{result['generated']}\n")
                f.write("-" * 60 + "\n\n")
        
        print(f"生成结果已保存到: {results_path}")
    
    def load_and_demo(self, model_path):
        """加载预训练模型并演示"""
        print(f"\n从 {model_path} 加载预训练模型...")
        
        try:
            from transformers import GPT2LMHeadModel, AutoTokenizer
            
            # 加载分词器
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            
            # 加载模型
            model = GPT2LMHeadModel.from_pretrained(model_path)
            model.to(self.config.device)
            
            print("✓ 模型加载成功")
            
            # 创建生成器
            generator = CodeGenerator(model, tokenizer, self.config)
            
            # 演示生成
            print("\n开始代码生成演示:")
            generator.demo_generation()
            
            return True
            
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False

# ==================== 第八部分：快速启动函数 ====================

def run_demo_training():
    """运行演示训练"""
    print("迷你GPT-2代码生成模型演示训练")
    print("-" * 50)
    print("注意: 这是一个演示版本，使用非常小的模型和数据集")
    print("训练将在几分钟内完成，适合学习和测试")
    print("-" * 50)
    
    # 创建并运行训练流程
    pipeline = DemoTrainingPipeline()
    pipeline.run()

def run_demo_inference(model_path=None):
    """运行演示推理"""
    if model_path is None:
        # 尝试从默认位置加载
        model_path = "./mini-codeparrot-demo/final_demo_model"
    
    print("代码生成演示推理")
    print("-" * 50)
    
    # 创建配置
    config = TrainingConfig()
    
    # 创建流水线并加载模型
    pipeline = DemoTrainingPipeline()
    pipeline.config = config
    
    if pipeline.load_and_demo(model_path):
        print("\n✓ 推理演示完成")
    else:
        print("\n✗ 推理演示失败，请先运行训练")

# ==================== 第九部分：命令行接口 ====================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="迷你GPT-2代码生成模型演示")
    parser.add_argument("--mode", type=str, default="train", 
                       choices=["train", "inference", "help"],
                       help="运行模式: train(训练), inference(推理), help(帮助)")
    parser.add_argument("--model_path", type=str, default=None,
                       help="预训练模型路径（推理模式使用）")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        run_demo_training()
    
    elif args.mode == "inference":
        run_demo_inference(args.model_path)
    
    elif args.mode == "help":
        print("""
迷你GPT-2代码生成模型演示
        
使用方式:
1. 训练模式: python demo_gpt2_training.py --mode train
   - 从头开始训练一个小型GPT-2模型
   - 使用微型数据集，训练速度快
   - 生成模型保存在 ./mini-codeparrot-demo/
        
2. 推理模式: python demo_gpt2_training.py --mode inference --model_path ./mini-codeparrot-demo/final_demo_model
   - 加载训练好的模型并生成代码
   - 如果没有指定模型路径，会尝试加载默认路径
        
3. 依赖安装: 
   pip install torch transformers matplotlib tqdm
        
注意: 这是一个演示版本，模型非常小，仅用于学习和测试目的。
        """)

# ==================== 第十部分：运行入口 ====================

if __name__ == "__main__":
    # 检查依赖
    required_packages = ["torch", "transformers", "matplotlib", "tqdm"]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("缺少必要的Python包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请使用以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        sys.exit(1)
    
    # 运行主程序
    main()
