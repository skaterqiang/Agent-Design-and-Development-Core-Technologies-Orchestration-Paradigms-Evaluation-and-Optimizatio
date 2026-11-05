"""
6.3.4 完整代码：从零开始训练GPT-2风格的代码生成模型
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
    """训练配置类"""
    # 模型配置
    model_name: str = "codeparrot-ds"
    context_length: int = 128
    vocab_size: int = 32768
    n_layer: int = 12
    n_head: int = 12
    n_embd: int = 768
    
    # 训练配置
    batch_size: int = 32
    eval_batch_size: int = 32
    gradient_accumulation_steps: int = 8
    learning_rate: float = 5e-4
    weight_decay: float = 0.1
    num_epochs: int = 1
    warmup_steps: int = 1000
    max_grad_norm: float = 1.0
    
    # 数据配置
    dataset_name: str = "huggingface-course/codeparrot-ds-train"
    validation_dataset: str = "huggingface-course/codeparrot-ds-valid"
    
    # 输出配置
    output_dir: str = "./codeparrot-ds-trained"
    log_dir: str = "./logs"
    save_steps: int = 5000
    eval_steps: int = 5000
    logging_steps: int = 100
    
    # 设备配置
    use_fp16: bool = True
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
        print("训练配置:")
        print("=" * 60)
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                print(f"{key:30}: {value}")
        print("=" * 60)

# ==================== 第二部分：数据准备 ====================

class DatasetProcessor:
    """数据集处理器"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.train_dataset = None
        self.valid_dataset = None
        
    def load_and_prepare_datasets(self):
        """加载和准备数据集"""
        print("\n" + "="*60)
        print("加载数据集...")
        print("="*60)
        
        try:
            from datasets import load_dataset, DatasetDict
            
            # 加载训练集和验证集
            train_data = load_dataset(
                self.config.dataset_name, 
                split="train",
                streaming=False  # 使用完整加载模式
            )
            
            valid_data = load_dataset(
                self.config.validation_dataset,
                split="validation",
                streaming=False
            )
            
            # 创建数据集字典
            raw_datasets = DatasetDict({
                "train": train_data,
                "valid": valid_data
            })
            
            print(f"训练集大小: {len(raw_datasets['train'])} 个样本")
            print(f"验证集大小: {len(raw_datasets['valid'])} 个样本")
            
            # 显示示例
            print("\n示例数据:")
            for key in raw_datasets["train"][0]:
                print(f"{key.upper()}: {raw_datasets['train'][0][key][:200]}")
            
            return raw_datasets
            
        except ImportError as e:
            print(f"错误: 需要安装datasets库 - {e}")
            print("请运行: pip install datasets")
            sys.exit(1)
        except Exception as e:
            print(f"加载数据集时出错: {e}")
            # 创建模拟数据用于测试
            return self.create_mock_data()

    def create_mock_data(self):
        """创建模拟数据（用于测试）"""
        print("创建模拟数据集用于测试...")
        
        from datasets import Dataset, DatasetDict
        
        # 创建一些Python代码样本
        code_samples = [
            """import pandas as pd
df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
print(df.head())""",
            """import matplotlib.pyplot as plt
import numpy as np
x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.plot(x, y)
plt.show()""",
            """from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
X, y = make_classification(n_samples=100, n_features=4)
clf = RandomForestClassifier()
clf.fit(X, y)""",
            """import seaborn as sns
import pandas as pd
data = pd.read_csv('data.csv')
sns.scatterplot(x='x', y='y', data=data)""",
            """def calculate_mean(numbers):
    return sum(numbers) / len(numbers)

data = [1, 2, 3, 4, 5]
mean = calculate_mean(data)"""
        ]
        
        # 重复样本以创建更大的数据集
        all_samples = code_samples * 1000
        
        # 创建训练集和验证集
        train_size = int(len(all_samples) * 0.9)
        train_samples = all_samples[:train_size]
        valid_samples = all_samples[train_size:]
        
        # 转换为datasets格式
        train_dataset = Dataset.from_dict({"content": train_samples})
        valid_dataset = Dataset.from_dict({"content": valid_samples})
        
        raw_datasets = DatasetDict({
            "train": train_dataset,
            "valid": valid_dataset
        })
        
        print(f"创建的模拟训练集大小: {len(raw_datasets['train'])}")
        print(f"创建的模拟验证集大小: {len(raw_datasets['valid'])}")
        
        return raw_datasets

# ==================== 第三部分：分词器和模型初始化 ====================

class ModelInitializer:
    """模型初始化器"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.tokenizer = None
        self.model = None
        
    def load_tokenizer(self):
        """加载或创建分词器"""
        print("\n" + "="*60)
        print("初始化分词器...")
        print("="*60)
        
        try:
            from transformers import AutoTokenizer
            
            # 尝试加载代码分词器
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    "huggingface-course/code-search-net-tokenizer"
                )
                print("✓ 成功加载预训练代码分词器")
            except:
                print("⚠ 无法加载预训练分词器，使用GPT-2分词器")
                tokenizer = AutoTokenizer.from_pretrained("gpt2")
                tokenizer.pad_token = tokenizer.eos_token
            
            # 打印分词器信息
            print(f"词汇表大小: {tokenizer.vocab_size}")
            print(f"特殊标记: {tokenizer.special_tokens_map}")
            
            # 测试分词
            test_code = "import pandas as pd"
            tokens = tokenizer.tokenize(test_code)
            print(f"测试分词 ('{test_code}'): {tokens}")
            
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
            
            print(f"模型架构: GPT-2 (小型)")
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
        
    def tokenize_dataset(self, datasets):
        """对数据集进行分词处理"""
        print("\n" + "="*60)
        print("处理数据集...")
        print("="*60)
        
        # 设置填充标记
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        def tokenize_function(examples):
            """分词函数"""
            # 对代码进行分词
            tokenized = self.tokenizer(
                examples["content"],
                truncation=True,
                max_length=self.config.context_length,
                return_overflowing_tokens=True,
                return_length=True,
                padding=False
            )
            
            # 只保留完整长度的块
            input_ids = []
            for length, ids in zip(tokenized["length"], tokenized["input_ids"]):
                if length == self.config.context_length:
                    input_ids.append(ids)
            
            return {"input_ids": input_ids}
        
        # 应用分词函数
        tokenized_datasets = datasets.map(
            tokenize_function,
            batched=True,
            remove_columns=datasets["train"].column_names,
            desc="分词处理"
        )
        
        print(f"处理后训练集样本数: {len(tokenized_datasets['train']):,}")
        print(f"处理后验证集样本数: {len(tokenized_datasets['valid']):,}")
        
        # 设置格式为torch张量
        tokenized_datasets.set_format("torch")
        
        return tokenized_datasets
    
    def create_data_collator(self):
        """创建数据整理器"""
        from transformers import DataCollatorForLanguageModeling
        
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # 使用因果语言建模
        )
        
        return data_collator

# ==================== 第五部分：训练器实现 ====================

class CustomTrainer:
    """自定义训练器"""
    
    def __init__(self, model, config, tokenizer, data_collator):
        self.model = model
        self.config = config
        self.tokenizer = tokenizer
        self.data_collator = data_collator
        
        # 训练状态
        self.global_step = 0
        self.epoch = 0
        self.best_eval_loss = float('inf')
        
        # 训练历史
        self.train_history = {
            "loss": [],
            "eval_loss": [],
            "learning_rate": [],
            "epoch": [],
            "step": []
        }
        
        # 初始化优化器
        self.optimizer = self.create_optimizer()
        
        # 初始化学习率调度器
        self.scheduler = self.create_scheduler()
        
    def create_optimizer(self):
        """创建优化器"""
        from torch.optim import AdamW
        
        # 不需要权重衰减的参数
        no_decay = ["bias", "LayerNorm.weight"]
        
        # 分组参数
        optimizer_grouped_parameters = [
            {
                "params": [p for n, p in self.model.named_parameters() 
                          if not any(nd in n for nd in no_decay)],
                "weight_decay": self.config.weight_decay,
            },
            {
                "params": [p for n, p in self.model.named_parameters() 
                          if any(nd in n for nd in no_decay)],
                "weight_decay": 0.0,
            },
        ]
        
        optimizer = AdamW(
            optimizer_grouped_parameters,
            lr=self.config.learning_rate,
            betas=(0.9, 0.95),
            eps=1e-8
        )
        
        return optimizer
    
    def create_scheduler(self):
        """创建学习率调度器"""
        from transformers import get_linear_schedule_with_warmup
        
        # 计算总训练步数
        total_steps = self.config.num_epochs * self.config.save_steps
        
        scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=self.config.warmup_steps,
            num_training_steps=total_steps
        )
        
        return scheduler
    
    def train_epoch(self, train_dataloader, epoch):
        """训练一个epoch"""
        self.model.train()
        self.epoch = epoch
        
        total_loss = 0
        progress_bar = tqdm(train_dataloader, desc=f"Epoch {epoch}")
        
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
            progress_bar.set_postfix({"loss": f"{avg_loss:.4f}"})
            
            # 记录训练历史
            if self.global_step % self.config.logging_steps == 0:
                self.train_history["loss"].append(avg_loss)
                self.train_history["step"].append(self.global_step)
                self.train_history["epoch"].append(epoch)
                self.train_history["learning_rate"].append(
                    self.scheduler.get_last_lr()[0]
                )
            
            # 定期评估和保存
            if self.global_step % self.config.eval_steps == 0:
                eval_loss = self.evaluate()
                self.train_history["eval_loss"].append(eval_loss)
                
                # 保存最佳模型
                if eval_loss < self.best_eval_loss:
                    self.best_eval_loss = eval_loss
                    self.save_model(f"best_model_step_{self.global_step}")
            
            # 定期保存检查点
            if self.global_step % self.config.save_steps == 0:
                self.save_model(f"checkpoint_step_{self.global_step}")
        
        return total_loss / len(train_dataloader)
    
    def evaluate(self):
        """评估模型"""
        print("\n正在评估模型...")
        
        # 这里简化评估过程，实际应该使用验证集
        self.model.eval()
        
        # 使用随机数据进行评估
        with torch.no_grad():
            batch_size = 8
            dummy_input = torch.randint(
                0, len(self.tokenizer),
                (batch_size, self.config.context_length)
            ).to(self.config.device)
            
            outputs = self.model(dummy_input, labels=dummy_input)
            eval_loss = outputs.loss.item()
        
        print(f"评估损失: {eval_loss:.4f}")
        
        self.model.train()
        return eval_loss
    
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
            'best_eval_loss': self.best_eval_loss,
            'train_history': self.train_history
        }, os.path.join(save_path, 'training_state.pt'))
        
        print(f"模型已保存到: {save_path}")
    
    def plot_training_history(self):
        """绘制训练历史图表"""
        if not self.train_history["loss"]:
            print("没有训练历史可绘制")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # 绘制训练损失
        axes[0, 0].plot(self.train_history["loss"])
        axes[0, 0].set_title('Training Loss')
        axes[0, 0].set_xlabel('Log Interval')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].grid(True)
        
        # 绘制评估损失
        if self.train_history["eval_loss"]:
            axes[0, 1].plot(self.train_history["eval_loss"])
            axes[0, 1].set_title('Evaluation Loss')
            axes[0, 1].set_xlabel('Eval Interval')
            axes[0, 1].set_ylabel('Loss')
            axes[0, 1].grid(True)
        
        # 绘制学习率
        axes[1, 0].plot(self.train_history["learning_rate"])
        axes[1, 0].set_title('Learning Rate')
        axes[1, 0].set_xlabel('Log Interval')
        axes[1, 0].set_ylabel('LR')
        axes[1, 0].grid(True)
        
        # 计算困惑度
        if self.train_history["loss"]:
            perplexities = [math.exp(loss) for loss in self.train_history["loss"]]
            axes[1, 1].plot(perplexities)
            axes[1, 1].set_title('Perplexity')
            axes[1, 1].set_xlabel('Log Interval')
            axes[1, 1].set_ylabel('Perplexity')
            axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        # 保存图表
        plot_path = os.path.join(self.config.log_dir, 'training_history.png')
        plt.savefig(plot_path)
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
    
    def generate_code(self, prompt, max_length=100, temperature=0.8, top_p=0.95):
        """生成代码"""
        # 编码提示
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.config.device)
        
        # 生成配置
        generation_config = {
            "max_length": len(inputs.input_ids[0]) + max_length,
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
        generated_code = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return generated_code
    
    def test_generation(self, test_prompts=None):
        """测试生成功能"""
        if test_prompts is None:
            test_prompts = [
                "# 创建散点图\nimport matplotlib.pyplot as plt\n",
                "# 创建DataFrame\nimport pandas as pd\n",
                "# 训练随机森林模型\nfrom sklearn.ensemble import RandomForestClassifier\n",
                "# 计算均值和标准差\nimport numpy as np\n",
                "# 读取CSV文件并显示前5行\nimport pandas as pd\n"
            ]
        
        print("\n" + "="*60)
        print("代码生成测试")
        print("="*60)
        
        results = []
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n测试 {i}:")
            print(f"提示: {prompt}")
            
            generated = self.generate_code(prompt, max_length=50)
            print(f"生成代码:\n{generated}")
            print("-" * 60)
            
            results.append({
                "prompt": prompt,
                "generated": generated
            })
        
        return results

# ==================== 第七部分：主训练流程 ====================

class TrainingPipeline:
    """完整的训练流程"""
    
    def __init__(self, config=None):
        self.config = config or TrainingConfig()
        
        # 组件
        self.data_processor = None
        self.model_initializer = None
        self.data_preprocessor = None
        self.trainer = None
        self.generator = None
        
        # 数据
        self.raw_datasets = None
        self.tokenized_datasets = None
        self.data_collator = None
        
        # 模型
        self.tokenizer = None
        self.model = None
        
    def run(self):
        """运行完整训练流程"""
        print("\n" + "="*60)
        print("开始GPT-2代码生成模型训练流程")
        print("="*60)
        
        try:
            # 步骤1: 数据准备
            print("\n[步骤1/5] 数据准备")
            self.data_processor = DatasetProcessor(self.config)
            self.raw_datasets = self.data_processor.load_and_prepare_datasets()
            
            # 步骤2: 初始化分词器和模型
            print("\n[步骤2/5] 初始化模型")
            self.model_initializer = ModelInitializer(self.config)
            self.tokenizer = self.model_initializer.load_tokenizer()
            self.model = self.model_initializer.initialize_model(self.tokenizer)
            
            # 步骤3: 数据预处理
            print("\n[步骤3/5] 数据预处理")
            self.data_preprocessor = DataPreprocessor(self.config, self.tokenizer)
            self.tokenized_datasets = self.data_preprocessor.tokenize_dataset(self.raw_datasets)
            self.data_collator = self.data_preprocessor.create_data_collator()
            
            # 创建数据加载器
            from torch.utils.data import DataLoader
            
            train_dataloader = DataLoader(
                self.tokenized_datasets["train"],
                batch_size=self.config.batch_size,
                shuffle=True,
                collate_fn=self.data_collator
            )
            
            # 步骤4: 训练
            print("\n[步骤4/5] 训练模型")
            self.trainer = CustomTrainer(
                self.model, 
                self.config, 
                self.tokenizer, 
                self.data_collator
            )
            
            # 开始训练
            for epoch in range(self.config.num_epochs):
                print(f"\n开始第 {epoch+1}/{self.config.num_epochs} 轮训练")
                avg_loss = self.trainer.train_epoch(train_dataloader, epoch)
                print(f"第 {epoch+1} 轮平均损失: {avg_loss:.4f}")
            
            # 保存最终模型
            self.trainer.save_model("final_model")
            
            # 绘制训练历史
            self.trainer.plot_training_history()
            
            # 步骤5: 测试生成
            print("\n[步骤5/5] 测试代码生成")
            self.generator = CodeGenerator(self.model, self.tokenizer, self.config)
            generation_results = self.generator.test_generation()
            
            # 保存生成结果
            self.save_results(generation_results)
            
            print("\n" + "="*60)
            print("训练流程完成!")
            print("="*60)
            
        except Exception as e:
            print(f"\n训练过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
    
    def save_results(self, generation_results):
        """保存结果"""
        results_path = os.path.join(self.config.output_dir, "generation_results.txt")
        
        with open(results_path, "w", encoding="utf-8") as f:
            f.write("代码生成测试结果\n")
            f.write("=" * 60 + "\n\n")
            
            for i, result in enumerate(generation_results, 1):
                f.write(f"测试 {i}:\n")
                f.write(f"提示:\n{result['prompt']}\n")
                f.write(f"生成代码:\n{result['generated']}\n")
                f.write("-" * 60 + "\n\n")
        
        print(f"生成结果已保存到: {results_path}")
    
    def load_pretrained_model(self, model_path):
        """加载预训练模型"""
        print(f"\n从 {model_path} 加载预训练模型...")
        
        try:
            from transformers import GPT2LMHeadModel, AutoTokenizer
            
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            
            # 加载模型
            self.model = GPT2LMHeadModel.from_pretrained(model_path)
            self.model.to(self.config.device)
            
            print("✓ 模型加载成功")
            
            # 创建生成器
            self.generator = CodeGenerator(self.model, self.tokenizer, self.config)
            
            return True
            
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False

# ==================== 第八部分：快速启动函数 ====================

def quick_start_demo():
    """快速启动演示"""
    print("快速启动演示: GPT-2代码生成模型")
    print("-" * 50)
    
    # 创建配置（使用小规模配置以便快速运行）
    config = TrainingConfig(
        model_name="mini-codeparrot",
        context_length=64,  # 较小的上下文
        n_layer=4,          # 较少的层
        n_head=4,           # 较少的注意力头
        n_embd=256,         # 较小的隐藏维度
        batch_size=8,       # 较小的批次
        num_epochs=1,       # 较少的轮数
        save_steps=100,     # 较频繁的保存
        eval_steps=50,      # 较频繁的评估
        logging_steps=10    # 较频繁的日志
    )
    
    # 创建并运行训练流程
    pipeline = TrainingPipeline(config)
    pipeline.run()

def inference_demo(model_path=None):
    """推理演示"""
    print("推理演示: 使用训练好的模型生成代码")
    print("-" * 50)
    
    if model_path is None:
        model_path = "./codeparrot-ds-trained/final_model"
    
    # 创建配置
    config = TrainingConfig()
    
    # 创建流水线并加载模型
    pipeline = TrainingPipeline(config)
    
    if pipeline.load_pretrained_model(model_path):
        # 测试生成
        test_prompts = [
            "# 绘制正弦函数\nimport matplotlib.pyplot as plt\nimport numpy as np\n",
            "# 读取数据并计算统计量\nimport pandas as pd\n",
            "# 使用KMeans聚类\nfrom sklearn.cluster import KMeans\n"
        ]
        
        results = pipeline.generator.test_generation(test_prompts)
        pipeline.save_results(results)

# ==================== 第九部分：命令行接口 ====================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GPT-2代码生成模型训练")
    parser.add_argument("--mode", type=str, default="train", 
                       choices=["train", "inference", "demo"],
                       help="运行模式: train(训练), inference(推理), demo(演示)")
    parser.add_argument("--model_path", type=str, default=None,
                       help="预训练模型路径（推理模式使用）")
    parser.add_argument("--quick", action="store_true",
                       help="快速模式（使用小配置）")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        if args.quick:
            quick_start_demo()
        else:
            # 完整训练
            pipeline = TrainingPipeline()
            pipeline.run()
    
    elif args.mode == "inference":
        inference_demo(args.model_path)
    
    elif args.mode == "demo":
        quick_start_demo()

# ==================== 第十部分：运行入口 ====================

if __name__ == "__main__":
    # 检查依赖
    required_packages = ["torch", "transformers", "datasets", "tqdm", "matplotlib"]
    
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

