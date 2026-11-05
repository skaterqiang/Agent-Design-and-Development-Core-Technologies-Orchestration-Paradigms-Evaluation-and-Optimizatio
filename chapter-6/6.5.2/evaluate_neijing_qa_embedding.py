# evaluate_neijing_qa_embedding.py
"""
功能：评估黄帝内经QA数据集的嵌入质量
使用方法：python evaluate_neijing_qa_embedding.py
输出：相似度统计结果和低质量数据文件
"""

import torch
import numpy as np
import json
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import traceback
import time
import os

def check_cuda_availability():
    """检查CUDA可用性"""
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        current_device = torch.cuda.current_device()
        device_name = torch.cuda.get_device_name(current_device)
        print(f"[INFO] CUDA可用，检测到 {device_count} 个GPU:")
        print(f"   当前使用设备 {current_device}: {device_name}")
        print(f"   CUDA版本: {torch.version.cuda}")
        print(f"   PyTorch CUDA支持: {torch.cuda.is_available()}")
        return True, current_device, device_name
    else:
        print("[WARN] CUDA不可用，将使用CPU进行计算")
        print(f"   PyTorch版本: {torch.__version__}")
        return False, None, None

def convert_tensor_to_numpy(tensor):
    """安全地将PyTorch张量转换为numpy数组，处理BFloat16类型"""
    if tensor.dtype == torch.bfloat16:
        # 将BFloat16转换为Float32
        return tensor.float().cpu().numpy()
    else:
        return tensor.cpu().numpy() if tensor.is_cuda else tensor.numpy()

def load_neijing_qa_data(data_file_path):
    """加载黄帝内经QA数据"""
    print("[INFO] 加载黄帝内经QA数据...")
    try:
        with open(data_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[SUCCESS] 数据加载成功，样本数量: {len(data)}")
        return data
    except Exception as e:
        print(f"[ERROR] 数据加载失败: {e}")
        traceback.print_exc()
        return None

def extract_qa_pairs(data):
    """从messages格式中提取问答对"""
    print("[INFO] 提取问答对...")
    qa_pairs = []
    
    for idx, item in enumerate(data):
        messages = item.get('messages', [])
        
        # 查找user和assistant消息
        user_message = None
        assistant_message = None
        
        for msg in messages:
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
            elif msg.get('role') == 'assistant':
                assistant_message = msg.get('content', '')
        
        # 确保都有内容才添加
        if user_message and assistant_message:
            qa_pairs.append({
                'id': idx,
                'question': user_message,
                'answer': assistant_message
            })
    
    print(f"[SUCCESS] 成功提取问答对数量: {len(qa_pairs)}")
    return qa_pairs

def evaluate_model_on_neijing_data():
    """主评估函数"""
    print("=" * 60)
    print("黄帝内经QA数据集嵌入质量评估")
    print("=" * 60)
    
    # 1. 检查CUDA可用性
    print("\n[STEP 1/5] 检查硬件配置...")
    cuda_available, device_id, device_name = check_cuda_availability()
    
    # 设置设备
    if cuda_available:
        device = torch.device(f"cuda:{device_id}")
        print(f"   使用设备: {device}")
        # 设置CUDA优化选项
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
    else:
        device = torch.device("cpu")
        print(f"   使用设备: CPU")
    
    # 设置模型路径
    model_dir = "D:/model/Qwen/Qwen3-Embedding-0.6B"
    
    # 2. 加载数据
    print("\n[STEP 2/5] 加载数据集...")
    # 使用绝对路径
    data_file = r"neijing_qa_messages_array_20260213_225226.json"
    
    if not os.path.exists(data_file):
        print(f"[ERROR] 数据文件不存在: {data_file}")
        return
    
    raw_data = load_neijing_qa_data(data_file)
    if raw_data is None:
        return
    
    # 提取问答对
    qa_pairs = extract_qa_pairs(raw_data)
    if not qa_pairs:
        print("[ERROR] 未找到有效的问答对")
        return
    
    # 3. 加载模型
    print("\n[STEP 3/5] 加载Qwen3-Embedding-0.6B模型...")
    try:
        model = SentenceTransformer(model_dir, trust_remote_code=True)
        model = model.to(device)
        model.eval()
        
        print(f"[SUCCESS] 模型加载成功")
        print(f"   模型所在设备: {next(model.parameters()).device}")
        print(f"   最大序列长度: {model.max_seq_length}")
        
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"   模型参数总数: {total_params:,}")
        print(f"   可训练参数: {trainable_params:,}")
        
        if cuda_available:
            gpu_memory_allocated = torch.cuda.memory_allocated(device_id) / 1024**3
            gpu_memory_cached = torch.cuda.memory_reserved(device_id) / 1024**3
            print(f"   GPU内存占用: {gpu_memory_allocated:.2f} GB")
            print(f"   GPU缓存内存: {gpu_memory_cached:.2f} GB")
            
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        traceback.print_exc()
        return
    
    # 4. 评估相似度
    print("\n[STEP 4/5] 计算问答对相似度...")
    similarities = []
    low_quality_pairs = []
    medium_quality_pairs = []
    
    # 设置阈值
    low_threshold = 0.7
    medium_threshold = 0.8
    
    # 批处理配置
    if cuda_available:
        batch_size = 16
        print(f"   使用批处理大小: {batch_size} (GPU模式)")
    else:
        batch_size = 8
        print(f"   使用批处理大小: {batch_size} (CPU模式)")
    
    # 准备批量处理数据
    questions = [pair['question'] for pair in qa_pairs]
    answers = [pair['answer'] for pair in qa_pairs]
    ids = [pair['id'] for pair in qa_pairs]
    
    print(f"   总样本数量: {len(questions)}")
    
    # 批量处理
    total_batches = (len(questions) + batch_size - 1) // batch_size
    print(f"   总批次数: {total_batches}")
    
    start_time = time.time()
    progress_bar = tqdm(range(total_batches), desc="批量处理进度", unit="批次")
    
    for batch_idx in progress_bar:
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(questions))
        
        batch_questions = questions[start_idx:end_idx]
        batch_answers = answers[start_idx:end_idx]
        batch_ids = ids[start_idx:end_idx]
        
        try:
            with torch.no_grad():
                # 编码问题和答案
                query_embeddings = model.encode(batch_questions,
                                              prompt_name="query",
                                              batch_size=len(batch_questions),
                                              convert_to_tensor=True,
                                              show_progress_bar=False,
                                              device=str(device))
                
                document_embeddings = model.encode(batch_answers,
                                                 batch_size=len(batch_answers),
                                                 convert_to_tensor=True,
                                                 show_progress_bar=False,
                                                 device=str(device))
            
            # 确保张量在正确设备上
            if cuda_available:
                query_embeddings = query_embeddings.to(device)
                document_embeddings = document_embeddings.to(device)
            
            # 计算余弦相似度
            cos_sims = torch.nn.functional.cosine_similarity(query_embeddings, document_embeddings)
            cos_sims_cpu = convert_tensor_to_numpy(cos_sims)
            
            # 处理结果
            for i, cos_sim in enumerate(cos_sims_cpu):
                original_idx = batch_ids[i]
                question = batch_questions[i]
                answer = batch_answers[i]
                
                cos_sim_float = float(cos_sim)
                similarities.append(cos_sim_float)
                
                # 分类处理
                if cos_sim_float < low_threshold:
                    low_quality_pairs.append({
                        'id': original_idx,
                        'question': question,
                        'answer': answer,
                        'similarity': cos_sim_float,
                        'category': 'low_quality'
                    })
                elif cos_sim_float < medium_threshold:
                    medium_quality_pairs.append({
                        'id': original_idx,
                        'question': question,
                        'answer': answer,
                        'similarity': cos_sim_float,
                        'category': 'medium_quality'
                    })
            
            # 更新进度条
            if similarities:
                avg_sim = np.mean(similarities)
                current_speed = (end_idx - start_idx) / (time.time() - start_time) if (time.time() - start_time) > 0 else 0
                progress_bar.set_postfix({
                    '平均相似度': f'{avg_sim:.4f}',
                    '低质量对': len(low_quality_pairs),
                    '中等质量对': len(medium_quality_pairs),
                    '速度': f'{current_speed:.1f}样本/秒'
                })
                
        except torch.cuda.OutOfMemoryError:
            print(f"\n[WARN] 批次 {batch_idx} GPU内存不足，减小批处理大小...")
            smaller_batch = max(1, batch_size // 2)
            print(f"   尝试减小批处理大小到: {smaller_batch}")
            batch_size = smaller_batch
            continue
            
        except Exception as e:
            print(f"\n[ERROR] 处理批次 {batch_idx} 时出错: {e}")
            traceback.print_exc()
            continue
    
    total_time = time.time() - start_time
    if total_time > 0 and len(questions) > 0:
        print(f"\n[SUCCESS] 批量处理完成，总耗时: {total_time:.2f}秒")
        print(f"处理速度: {len(questions)/total_time:.2f} 样本/秒")
    else:
        print(f"\n[INFO] 批量处理完成")
    
    # 5. 生成报告
    print("\n[STEP 5/5] 生成评估报告...")
    if similarities:
        similarities_array = np.array(similarities)
        
        print(f"\n{'='*60}")
        print("评估结果统计")
        print(f"{'='*60}")
        print(f"总样本数: {len(similarities)}")
        print(f"低质量样本数(相似度<{low_threshold}): {len(low_quality_pairs)} ({len(low_quality_pairs)/len(similarities)*100:.1f}%)")
        print(f"中等质量样本数(相似度<{medium_threshold}): {len(medium_quality_pairs)} ({len(medium_quality_pairs)/len(similarities)*100:.1f}%)")
        print(f"高质量样本数(相似度>={medium_threshold}): {len(similarities)-len(low_quality_pairs)-len(medium_quality_pairs)} ({(len(similarities)-len(low_quality_pairs)-len(medium_quality_pairs))/len(similarities)*100:.1f}%)")
        print(f"平均相似度: {similarities_array.mean():.4f}")
        print(f"相似度中位数: {np.median(similarities_array):.4f}")
        print(f"相似度标准差: {similarities_array.std():.4f}")
        print(f"最低相似度: {similarities_array.min():.4f}")
        print(f"最高相似度: {similarities_array.max():.4f}")
        print(f"相似度分布:")
        for percentile in [10, 25, 50, 75, 90]:
            print(f"  {percentile}%分位数: {np.percentile(similarities_array, percentile):.4f}")
        
        # 保存结果文件
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 保存低质量数据
        if low_quality_pairs:
            output_file_low = f"neijing_low_quality_pairs_{timestamp}.json"
            with open(output_file_low, 'w', encoding='utf-8') as f:
                json.dump(low_quality_pairs, f, ensure_ascii=False, indent=2)
            print(f"\n低质量问答对已保存至: {output_file_low}")
        
        # 保存中等质量数据
        if medium_quality_pairs:
            output_file_medium = f"neijing_medium_quality_pairs_{timestamp}.json"
            with open(output_file_medium, 'w', encoding='utf-8') as f:
                json.dump(medium_quality_pairs, f, ensure_ascii=False, indent=2)
            print(f"中等质量问答对已保存至: {output_file_medium}")
            
            # 合并低质量和中等质量数据
            all_below_threshold = low_quality_pairs + medium_quality_pairs
            output_file_all = f"neijing_all_below_threshold_{timestamp}.json"
            with open(output_file_all, 'w', encoding='utf-8') as f:
                json.dump(all_below_threshold, f, ensure_ascii=False, indent=2)
            print(f"所有低于阈值的问答对已保存至: {output_file_all}")
            
            # CSV格式
            csv_file = f"neijing_below_threshold_{timestamp}.csv"
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.write("ID,相似度,类别,问题,答案\n")
                for item in all_below_threshold:
                    question_clean = item['question'].replace('"', '""').replace('\n', ' ').replace('\r', ' ')
                    answer_clean = item['answer'].replace('"', '""').replace('\n', ' ').replace('\r', ' ')
                    f.write(f"{item['id']},{item['similarity']:.4f},{item['category']},\"{question_clean}\",\"{answer_clean}\"\n")
            print(f"CSV格式数据已保存至: {csv_file}")
            
            # 保存统计信息
            stats = {
                "dataset": "黄帝内经QA数据集",
                "device_used": str(device),
                "cuda_available": cuda_available,
                "device_name": device_name,
                "processing_speed": f"{len(questions)/total_time:.2f} samples/sec" if total_time > 0 else "N/A",
                "total_time_seconds": total_time,
                "total_samples": len(similarities),
                "low_quality_samples": len(low_quality_pairs),
                "medium_quality_samples": len(medium_quality_pairs),
                "high_quality_samples": len(similarities) - len(low_quality_pairs) - len(medium_quality_pairs),
                "low_threshold": low_threshold,
                "medium_threshold": medium_threshold,
                "mean_similarity": float(similarities_array.mean()),
                "median_similarity": float(np.median(similarities_array)),
                "std_similarity": float(similarities_array.std()),
                "min_similarity": float(similarities_array.min()),
                "max_similarity": float(similarities_array.max()),
                "percentiles": {
                    "10": float(np.percentile(similarities_array, 10)),
                    "25": float(np.percentile(similarities_array, 25)),
                    "50": float(np.percentile(similarities_array, 50)),
                    "75": float(np.percentile(similarities_array, 75)),
                    "90": float(np.percentile(similarities_array, 90))
                }
            }
            
            stats_file = f"neijing_evaluation_stats_{timestamp}.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f"评估统计信息已保存至: {stats_file}")
            
            # 显示样本详情
            print(f"\n{'='*60}")
            print("前5个低质量样本详情:")
            print(f"{'='*60}")
            for i, pair in enumerate(low_quality_pairs[:5]):
                print(f"\n样本 {i+1} (ID: {pair['id']}, 相似度: {pair['similarity']:.4f}):")
                print(f"问题: {pair['question'][:100]}..." if len(pair['question']) > 100 else f"问题: {pair['question']}")
                print(f"答案: {pair['answer'][:100]}..." if len(pair['answer']) > 100 else f"答案: {pair['answer']}")
            
            print(f"\n{'='*60}")
            print(f"前5个中等质量样本详情:")
            print(f"{'='*60}")
            for i, pair in enumerate(medium_quality_pairs[:5]):
                print(f"\n样本 {i+1} (ID: {pair['id']}, 相似度: {pair['similarity']:.4f}):")
                print(f"问题: {pair['question'][:100]}..." if len(pair['question']) > 100 else f"问题: {pair['question']}")
                print(f"答案: {pair['answer'][:100]}..." if len(pair['answer']) > 100 else f"答案: {pair['answer']}")
    else:
        print("[WARN] 没有成功计算相似度的样本")
    
    print(f"\n{'='*60}")
    print("评估完成！")
    print(f"{'='*60}")
    
    # 清空GPU缓存
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        print(f"\n[INFO] 已清理GPU内存缓存")

if __name__ == "__main__":
    # 设置PyTorch内存管理选项
    torch.cuda.empty_cache()
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    
    try:
        evaluate_model_on_neijing_data()
    except Exception as e:
        print(f"[ERROR] 程序执行出错: {e}")
        traceback.print_exc()
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()