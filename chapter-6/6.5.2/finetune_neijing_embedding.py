# finetune_neijing_embedding.py
"""
功能：微调Qwen3-Embedding-0.6B模型用于黄帝内经QA数据
使用方法：python finetune_neijing_embedding.py --data_file neijing_low_quality_pairs_20260214_200701.json
参数：--epochs 训练轮数，默认2（小数据集建议1-3轮）
     --batch_size 批大小，默认16（根据GPU内存调整）
     --learning_rate 学习率，默认2e-5（针对领域数据调整）
"""

import json
import argparse
import torch
import numpy as np
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, losses, InputExample
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments
from datetime import datetime
import os
from datasets import Dataset
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from transformers.integrations import TensorBoardCallback

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 模型路径配置 - 使用绝对路径
MODEL_PATH = "D:/model/Qwen/Qwen3-Embedding-0.6B"
BASE_DIR = r"D:\智能体设计开发实战：核心技术、编排模式、评估与调优\code\chapter-6\6.5.2"
DEFAULT_DATA_FILE = os.path.join(BASE_DIR, "neijing_low_quality_pairs_20260214_200701.json")

@dataclass
class NeijingTrainingConfig:
    """黄帝内经训练配置数据类"""
    data_file: str = DEFAULT_DATA_FILE
    epochs: int = 2
    batch_size: int = 16
    learning_rate: float = 2e-5  # 针对领域数据稍微提高学习率
    weight_decay: float = 0.01
    max_samples: Optional[int] = None
    validation_split: float = 0.15  # 稍微增加验证集比例
    output_dir: str = field(default_factory=lambda: os.path.join(BASE_DIR, f"output/neijing_finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    use_amp: bool = True
    tensorboard_logdir: str = field(default_factory=lambda: os.path.join(BASE_DIR, f"runs/neijing_finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
    # 领域特定参数
    domain_specific_lr: bool = True  # 是否使用领域特定的学习率调整

def load_neijing_data(file_path: str) -> List[Dict]:
    """加载黄帝内经低质量数据"""
    logger.info(f"[INFO] 加载黄帝内经数据: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"数据文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"[SUCCESS] 成功加载 {len(data)} 个低质量样本")
    
    # 显示数据样本结构
    if data:
        sample = data[0]
        logger.info(f"[INFO] 数据结构示例: {list(sample.keys())}")
        logger.info(f"[INFO] 样本内容示例:")
        logger.info(f"  ID: {sample.get('id')}")
        logger.info(f"  问题: {sample.get('question', '')[:50]}...")
        logger.info(f"  答案: {sample.get('answer', '')[:50]}...")
        logger.info(f"  相似度: {sample.get('similarity', 'N/A')}")
        logger.info(f"  类别: {sample.get('category', 'N/A')}")
    
    return data

def prepare_neijing_training_data(data: List[Dict], config: NeijingTrainingConfig) -> Tuple[Dataset, Optional[Dataset], List[Tuple[str, str]], List[Tuple[str, str]]]:
    """准备黄帝内经训练和验证数据"""
    
    train_pairs = []
    val_pairs = []
    
    logger.info("[INFO] 准备训练数据...")
    
    for idx, item in enumerate(data):
        if config.max_samples and idx >= config.max_samples:
            break
            
        question = item.get('question', '').strip()
        answer = item.get('answer', '').strip()
        
        if question and answer:
            # 存储为文本对
            text_pair = (question, answer)
            
            # 按比例分割训练和验证集
            if config.validation_split > 0 and np.random.random() < config.validation_split:
                val_pairs.append(text_pair)
            else:
                train_pairs.append(text_pair)
        else:
            logger.warning(f"[WARN] 跳过无效样本 ID: {item.get('id', 'unknown')}")
    
    logger.info(f"[INFO] 训练样本: {len(train_pairs)}, 验证样本: {len(val_pairs)}")
    
    # 转换为Hugging Face Dataset格式
    if train_pairs:
        train_texts1 = [pair[0] for pair in train_pairs]
        train_texts2 = [pair[1] for pair in train_pairs]
        train_dataset = Dataset.from_dict({
            'sentence1': train_texts1,
            'sentence2': train_texts2
        })
    else:
        train_dataset = Dataset.from_dict({'sentence1': [], 'sentence2': []})
        logger.error("[ERROR] 没有可用的训练样本")
    
    val_dataset = None
    if val_pairs:
        val_texts1 = [pair[0] for pair in val_pairs]
        val_texts2 = [pair[1] for pair in val_pairs]
        val_dataset = Dataset.from_dict({
            'sentence1': val_texts1,
            'sentence2': val_texts2
        })
    
    return train_dataset, val_dataset, train_pairs, val_pairs

def prepare_neijing_evaluator(val_pairs: List[Tuple[str, str]]) -> Optional[EmbeddingSimilarityEvaluator]:
    """准备黄帝内经数据的评估器"""
    if not val_pairs:
        logger.warning("[WARN] 没有验证数据，跳过评估器准备")
        return None
    
    sentences1, sentences2, scores = [], [], []
    
    for pair in val_pairs:
        if len(pair) >= 2:
            sentences1.append(pair[0])
            sentences2.append(pair[1])
            scores.append(1.0)  # 对于QA对，我们假设它们是相关的
    
    if not sentences1 or not sentences2:
        logger.warning("[WARN] 评估数据为空")
        return None
    
    evaluator = EmbeddingSimilarityEvaluator(
        sentences1=sentences1,
        sentences2=sentences2,
        scores=scores,
        name='neijing_qa_similarity',
        write_csv=True,
        main_similarity='cosine',
        show_progress_bar=False
    )
    
    logger.info(f"[SUCCESS] 评估器准备完成，包含 {len(sentences1)} 个验证样本")
    return evaluator

def compute_neijing_similarities(model: SentenceTransformer, data: List[Dict], 
                                batch_size: int = 32) -> List[float]:
    """计算黄帝内经问答对的相似度"""
    logger.info("[INFO] 计算问答对相似度...")
    
    questions = []
    answers = []
    
    for item in data:
        question = item.get('question', '').strip()
        answer = item.get('answer', '').strip()
        if question and answer:
            questions.append(question)
            answers.append(answer)
    
    if len(questions) != len(answers):
        logger.warning(f"[WARN] 问题和答案数量不匹配: {len(questions)} vs {len(answers)}")
        return []
    
    if not questions:
        logger.warning("[WARN] 没有有效的问答对用于相似度计算")
        return []
    
    # 批量编码
    try:
        question_embeds = model.encode(
            questions,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_tensor=True,
            normalize_embeddings=True
        )
        
        answer_embeds = model.encode(
            answers,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_tensor=True,
            normalize_embeddings=True
        )
        
        # 计算余弦相似度
        similarities = []
        for q_emb, a_emb in zip(question_embeds, answer_embeds):
            sim = torch.cosine_similarity(q_emb.unsqueeze(0), a_emb.unsqueeze(0)).item()
            similarities.append(sim)
        
        logger.info(f"[SUCCESS] 成功计算 {len(similarities)} 个相似度值")
        return similarities
        
    except Exception as e:
        logger.error(f"[ERROR] 相似度计算失败: {e}")
        return []

def save_neijing_results(data: List[Dict], similarities: List[float], output_dir: str) -> str:
    """保存黄帝内经微调结果"""
    if not similarities:
        logger.warning("[WARN] 没有相似度数据可保存")
        return ""
    
    # 创建结果列表
    results = []
    for item, sim in zip(data, similarities):
        result_item = item.copy()
        result_item['finetuned_similarity'] = float(sim)
        results.append(result_item)
    
    # 按相似度排序
    results.sort(key=lambda x: x['finetuned_similarity'], reverse=True)
    
    # 计算统计信息
    sim_values = [item['finetuned_similarity'] for item in results]
    stats = {
        "total_pairs": len(results),
        "similarity_mean": float(np.mean(sim_values)),
        "similarity_std": float(np.std(sim_values)),
        "similarity_min": float(np.min(sim_values)),
        "similarity_max": float(np.max(sim_values)),
        "similarity_median": float(np.median(sim_values)),
        "pairs_above_0.8": int(sum(1 for s in sim_values if s > 0.8)),
        "pairs_above_0.7": int(sum(1 for s in sim_values if s > 0.7)),
        "pairs_above_0.6": int(sum(1 for s in sim_values if s > 0.6)),
        "pairs_below_0.4": int(sum(1 for s in sim_values if s < 0.4)),
        "improvement_threshold": 0.7  # 设定改进阈值
    }
    
    # 保存到文件
    output_path = os.path.join(output_dir, "neijing_similarity_results.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "statistics": stats,
            "pairs": results
        }, f, ensure_ascii=False, indent=2)
    
    logger.info("[INFO] 相似度统计:")
    logger.info(f"  总样本数: {stats['total_pairs']}")
    logger.info(f"  平均相似度: {stats['similarity_mean']:.4f}")
    logger.info(f"  相似度标准差: {stats['similarity_std']:.4f}")
    logger.info(f"  相似度范围: [{stats['similarity_min']:.4f}, {stats['similarity_max']:.4f}]")
    logger.info(f"  中位数相似度: {stats['similarity_median']:.4f}")
    logger.info(f"  高质量样本(>0.7): {stats['pairs_above_0.7']} ({stats['pairs_above_0.7']/stats['total_pairs']*100:.1f}%)")
    logger.info(f"  低质量样本(<0.4): {stats['pairs_below_0.4']} ({stats['pairs_below_0.4']/stats['total_pairs']*100:.1f}%)")
    
    return output_path

def finetune_neijing_model(args):
    """黄帝内经模型微调主函数"""
    logger.info("=" * 60)
    logger.info("黄帝内经QA数据 Qwen3-Embedding-0.6B 模型微调")
    logger.info("=" * 60)
    
    # 创建配置
    config = NeijingTrainingConfig(
        data_file=args.data_file,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        max_samples=args.max_samples,
        validation_split=args.validation_split,
        output_dir=args.output_dir if hasattr(args, 'output_dir') and args.output_dir else 
                   f"output/neijing_finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        use_amp=args.use_amp if hasattr(args, 'use_amp') else True,
        tensorboard_logdir=args.tensorboard_logdir if hasattr(args, 'tensorboard_logdir') and args.tensorboard_logdir else 
                          f"runs/neijing_finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    # 确保输出目录存在
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(config.tensorboard_logdir), exist_ok=True)
    
    # 1. 加载数据
    logger.info("\n[STEP 1/6] 加载训练数据...")
    try:
        data = load_neijing_data(config.data_file)
    except Exception as e:
        logger.error(f"[ERROR] 数据加载失败: {e}")
        return
    
    # 2. 准备训练数据
    logger.info("\n[STEP 2/6] 准备训练数据...")
    train_dataset, val_dataset, train_pairs, val_pairs = prepare_neijing_training_data(data, config)
    
    if len(train_dataset) == 0:
        logger.error("[ERROR] 没有可用的训练样本")
        return
    
    # 3. 加载模型
    logger.info("\n[STEP 3/6] 加载预训练模型...")
    try:
        model = SentenceTransformer(MODEL_PATH)
        model.to(config.device)
        model = model.float()
        
        logger.info(f"[SUCCESS] 模型加载成功")
        logger.info(f"  模型维度: {model.get_sentence_embedding_dimension()}")
        logger.info(f"  设备: {config.device}")
        logger.info(f"  模型路径: {MODEL_PATH}")
        
    except Exception as e:
        logger.error(f"[ERROR] 模型加载失败: {e}")
        return
    
    # 4. 计算原始相似度
    logger.info("\n[STEP 4/6] 计算原始相似度...")
    original_similarities = compute_neijing_similarities(model, data, config.batch_size)
    
    # 5. 准备评估器
    logger.info("\n[STEP 5/6] 准备评估器...")
    evaluator = prepare_neijing_evaluator(val_pairs)
    
    # 6. 准备训练参数
    logger.info("\n[STEP 6/6] 准备训练参数...")
    
    total_steps = len(train_dataset) * config.epochs // config.batch_size
    warmup_steps = int(total_steps * 0.1)
    
    logger.info(f"\n训练配置详情:")
    logger.info(f"  训练轮数: {config.epochs}")
    logger.info(f"  批次大小: {config.batch_size}")
    logger.info(f"  学习率: {config.learning_rate}")
    logger.info(f"  权重衰减: {config.weight_decay}")
    logger.info(f"  Warmup步数: {warmup_steps}")
    logger.info(f"  总训练步数: {total_steps}")
    logger.info(f"  训练样本数: {len(train_dataset)}")
    logger.info(f"  验证样本数: {len(val_dataset) if val_dataset else 0}")
    logger.info(f"  输出目录: {config.output_dir}")
    logger.info(f"  TensorBoard日志: {config.tensorboard_logdir}")
    logger.info(f"  自动混合精度: {config.use_amp}")
    
    # 针对黄帝内经领域的训练参数调整
    training_args = SentenceTransformerTrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        warmup_steps=warmup_steps,
        # 使用正确的参数名
        use_cpu=not torch.cuda.is_available(),  # 如果没有GPU则使用CPU
        fp16=config.use_amp and torch.cuda.is_available(),  # 只在有GPU时启用FP16
        logging_dir=config.tensorboard_logdir,
        logging_steps=5,  # 更频繁的日志记录
        save_steps=50,
        save_total_limit=3,
        remove_unused_columns=False,
        report_to="tensorboard",
    )
    
    # 使用MultipleNegativesRankingLoss进行对比学习
    loss = losses.MultipleNegativesRankingLoss(model)
    
    logger.info("\n" + "=" * 60)
    logger.info("开始模型微调训练...")
    logger.info("=" * 60)
    
    try:
        # 创建训练器
        trainer = SentenceTransformerTrainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            loss=loss,
            evaluator=evaluator,
        )
        
        # 开始训练
        trainer.train()
        
        # 保存最终模型
        final_model_path = os.path.join(config.output_dir, "final_model")
        model.save(final_model_path)
        logger.info(f"\n[SUCCESS] 训练完成！模型保存至: {final_model_path}")
        
        # 保存训练配置
        config_dict = {
            "model_path": MODEL_PATH,
            "data_file": config.data_file,
            "train_samples": len(train_dataset),
            "val_samples": len(val_dataset) if val_dataset else 0,
            "epochs": config.epochs,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "weight_decay": config.weight_decay,
            "validation_split": config.validation_split,
            "finetuned_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "device": config.device,
            "use_amp": config.use_amp,
            "tensorboard_logdir": config.tensorboard_logdir,
            "domain_specific": "黄帝内经中医领域",
            "training_args": str(training_args),
        }
        
        config_file = os.path.join(config.output_dir, "training_config.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"[INFO] 训练配置保存至: {config_file}")
        
        # 启动TensorBoard提示
        logger.info(f"\n[TENSORBOARD] TensorBoard日志已保存至: {config.tensorboard_logdir}")
        logger.info("启动TensorBoard查看训练指标:")
        logger.info(f"  tensorboard --logdir={os.path.dirname(config.tensorboard_logdir)}")
        
    except Exception as e:
        logger.error(f"[ERROR] 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 7. 计算微调后的相似度
    logger.info("\n[POST-TRAINING] 计算微调后相似度...")
    
    try:
        # 重新加载最佳模型
        best_model_path = os.path.join(config.output_dir, "final_model")
        if not os.path.exists(best_model_path):
            best_model_path = config.output_dir
        
        logger.info(f"[INFO] 加载微调后模型: {best_model_path}")
        finetuned_model = SentenceTransformer(best_model_path)
        finetuned_model.to(config.device)
        
        # 计算相似度
        finetuned_similarities = compute_neijing_similarities(
            finetuned_model, data, config.batch_size
        )
        
        if finetuned_similarities:
            # 保存结果
            results_path = save_neijing_results(data, finetuned_similarities, config.output_dir)
            logger.info(f"[SUCCESS] 相似度结果保存至: {results_path}")
            
            # 对比原始相似度
            if original_similarities and len(original_similarities) == len(finetuned_similarities):
                logger.info("\n[COMPARISON] 训练前后相似度对比:")
                
                # 计算改进统计
                improvements = []
                degradation = []
                unchanged = 0
                
                for i, (orig, new) in enumerate(zip(original_similarities, finetuned_similarities)):
                    diff = new - orig
                    if diff > 0.01:  # 显著提升
                        improvements.append(diff)
                    elif diff < -0.01:  # 显著下降
                        degradation.append(abs(diff))
                    else:
                        unchanged += 1
                
                logger.info(f"  总样本数: {len(data)}")
                logger.info(f"  相似度提升样本: {len(improvements)} ({len(improvements)/len(data)*100:.1f}%)")
                logger.info(f"  相似度下降样本: {len(degradation)} ({len(degradation)/len(data)*100:.1f}%)")
                logger.info(f"  无显著变化样本: {unchanged} ({unchanged/len(data)*100:.1f}%)")
                
                if improvements:
                    avg_improvement = np.mean(improvements)
                    max_improvement = np.max(improvements)
                    logger.info(f"  平均提升幅度: {avg_improvement:.4f}")
                    logger.info(f"  最大提升幅度: {max_improvement:.4f}")
                
                if degradation:
                    avg_degradation = np.mean(degradation)
                    max_degradation = np.max(degradation)
                    logger.info(f"  平均下降幅度: {avg_degradation:.4f}")
                    logger.info(f"  最大下降幅度: {max_degradation:.4f}")
                
                # 计算整体统计
                orig_mean = np.mean(original_similarities)
                new_mean = np.mean(finetuned_similarities)
                overall_improvement = new_mean - orig_mean
                
                logger.info(f"\n[OVERALL STATISTICS]")
                logger.info(f"  原始平均相似度: {orig_mean:.4f}")
                logger.info(f"  微调后平均相似度: {new_mean:.4f}")
                logger.info(f"  整体改进: {overall_improvement:+.4f}")
    
    except Exception as e:
        logger.error(f"[ERROR] 计算相似度失败: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info("黄帝内经模型微调完成！")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="微调Qwen3-Embedding-0.6B模型用于黄帝内经QA数据")
    
    # 参数设置
    parser.add_argument("--data_file", type=str, default=DEFAULT_DATA_FILE,
                       help=f"黄帝内经低质量数据文件路径 (默认: {DEFAULT_DATA_FILE})")
    parser.add_argument("--epochs", type=int, default=2,
                       help="训练轮数，默认2（小数据集建议1-3轮）")
    parser.add_argument("--batch_size", type=int, default=16,
                       help="批大小，默认16（根据GPU内存调整）")
    parser.add_argument("--learning_rate", type=float, default=2e-5,
                       help="学习率，默认2e-5（针对领域数据调整）")
    parser.add_argument("--weight_decay", type=float, default=0.01,
                       help="权重衰减，默认0.01（防止过拟合）")
    parser.add_argument("--max_samples", type=int, default=None,
                       help="最大训练样本数，默认使用全部")
    parser.add_argument("--validation_split", type=float, default=0.15,
                       help="验证集比例，默认0.15")
    parser.add_argument("--output_dir", type=str, default="",
                       help="输出目录，默认自动生成")
    parser.add_argument("--tensorboard_logdir", type=str, default="",
                       help="TensorBoard日志目录，默认自动生成")
    parser.add_argument("--use_amp", action="store_true", default=True,
                       help="是否使用自动混合精度训练，默认True")
    
    args = parser.parse_args()
    
    # 如果提供了相对路径，转换为绝对路径
    if not os.path.isabs(args.data_file):
        args.data_file = os.path.join(BASE_DIR, args.data_file)
    
    # 如果输出目录未指定，使用默认值
    if not args.output_dir:
        args.output_dir = os.path.join(BASE_DIR, f"output/neijing_finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    if not args.tensorboard_logdir:
        args.tensorboard_logdir = os.path.join(BASE_DIR, f"runs/neijing_finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # 参数验证和警告
    if args.learning_rate > 5e-5:
        logger.warning(f"[WARN] 学习率 {args.learning_rate} 可能过高，建议使用1e-5到3e-5之间的值")
    
    if args.batch_size > 32:
        logger.warning(f"[WARN] 批大小 {args.batch_size} 可能过大，可能导致内存溢出")
    
    if args.epochs > 5:
        logger.warning(f"[WARN] 训练轮数 {args.epochs} 可能过多，小数据集容易过拟合")
    
    # 显示参数
    logger.info("[PARAMETERS] 训练参数:")
    for arg_name, arg_value in vars(args).items():
        logger.info(f"  {arg_name}: {arg_value}")
    
    # 检查CUDA和硬件
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"[HARDWARE] 检测到GPU: {device_name}")
        if not args.use_amp:
            logger.warning("[WARN] 未启用AMP，训练速度可能较慢")
    else:
        logger.warning("[WARN] 未检测到GPU，使用CPU训练可能会非常慢")
        if args.use_amp:
            logger.warning("[INFO] CPU不支持AMP，将自动禁用AMP")
        if args.batch_size > 8:
            logger.warning("[WARN] CPU环境下建议使用较小的批大小(≤8)")
    
    # 执行训练
    finetune_neijing_model(args)