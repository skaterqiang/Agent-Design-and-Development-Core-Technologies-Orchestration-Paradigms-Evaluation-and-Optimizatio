import transformers
import torch
import os
import json
import random
import numpy as np
import argparse
from torch.utils.tensorboard import SummaryWriter
from datetime import datetime
from tqdm import tqdm
from torch.nn import DataParallel
from tokenizations.bpe_tokenizer import get_encoder


def build_files(data_path, tokenized_data_path, num_pieces, full_tokenizer, min_length):
    """
    将原始语料分片并进行token化处理，保存为多个文件。
    """
    with open(data_path, 'r', encoding='utf8') as f:
        print('正在读取行数据...')
        lines = json.load(f)
        # 使用 [SEP] 表示换行符，段落之间用 [SEP] 分隔
        lines = [line.replace('\n', ' [SEP] ') for line in lines]
    
    all_len = len(lines)
    if not os.path.exists(tokenized_data_path):
        os.mkdir(tokenized_data_path)

    for i in tqdm(range(num_pieces)):
        # 将数据划分为 num_pieces 份
        sublines = lines[all_len // num_pieces * i: all_len // num_pieces * (i + 1)]
        if i == num_pieces - 1:
            # 最后一份包含剩余的所有数据
            sublines.extend(lines[all_len // num_pieces * (i + 1):])
        
        # 过滤掉长度小于 min_length 的句子，并进行 token 化
        sublines = [full_tokenizer.tokenize(line) for line in sublines if len(line) > min_length]
        sublines = [full_tokenizer.convert_tokens_to_ids(line) for line in sublines]

        full_line = []
        for subline in sublines:
            # 在每篇文章开头添加 [MASK] 表示文章开始
            full_line.append(full_tokenizer.convert_tokens_to_ids('[MASK]'))
            full_line.extend(subline)
            # 在每篇文章结尾添加 [CLS] 表示文章结束
            full_line.append(full_tokenizer.convert_tokens_to_ids('[CLS]'))

        # 保存 tokenized 后的数据到文件
        with open(os.path.join(tokenized_data_path, f'tokenized_train_{i}.txt'), 'w') as f:
            for id in full_line:
                f.write(str(id) + ' ')
    print('数据构建完成')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', default='0,1,2,3', type=str, required=False, help='指定使用的 GPU 编号')
    parser.add_argument('--model_config', default='config/model_config_small.json', type=str, required=False,
                        help='模型配置文件路径')
    parser.add_argument('--tokenizer_path', default='cache/vocab_small.txt', type=str, required=False, help='词表路径')
    parser.add_argument('--raw_data_path', default='data/train.json', type=str, required=False, help='原始训练语料路径')
    parser.add_argument('--tokenized_data_path', default='data/tokenized/', type=str, required=False,
                        help='tokenized 语料保存路径')
    parser.add_argument('--raw', action='store_true', help='是否从原始语料重新构建 tokenized 数据')
    parser.add_argument('--epochs', default=5, type=int, required=False, help='训练轮数')
    parser.add_argument('--batch_size', default=8, type=int, required=False, help='训练批次大小')
    parser.add_argument('--lr', default=1.5e-4, type=float, required=False, help='学习率')
    parser.add_argument('--warmup_steps', default=2000, type=int, required=False, help='学习率预热步数')
    parser.add_argument('--log_step', default=1, type=int, required=False,
                        help='每隔多少步记录一次 loss（应为 gradient_accumulation 的整数倍）')
    parser.add_argument('--stride', default=768, type=int, required=False, help='训练时滑动窗口的步长')
    parser.add_argument('--gradient_accumulation', default=1, type=int, required=False, help='梯度累积步数')
    parser.add_argument('--fp16', action='store_true', help='是否启用混合精度训练（FP16）')
    parser.add_argument('--fp16_opt_level', default='O1', type=str, required=False, help='FP16 优化等级')
    parser.add_argument('--max_grad_norm', default=1.0, type=float, required=False, help='梯度裁剪阈值')
    parser.add_argument('--num_pieces', default=100, type=int, required=False, help='将训练语料划分为多少份')
    parser.add_argument('--min_length', default=128, type=int, required=False, help='最小收录文章长度（字符数）')
    parser.add_argument('--output_dir', default='model/', type=str, required=False, help='模型输出目录')
    parser.add_argument('--pretrained_model', default='', type=str, required=False, help='预训练模型路径（用于继续训练）')
    parser.add_argument('--writer_dir', default='tensorboard_summary/', type=str, required=False, help='TensorBoard 日志目录')
    parser.add_argument('--segment', action='store_true', help='中文是否按词切分（而非字）')
    parser.add_argument('--bpe_token', action='store_true', help='是否使用 BPE 子词切分')
    parser.add_argument('--encoder_json', default="tokenizations/encoder.json", type=str, help="BPE encoder.json 路径")
    parser.add_argument('--vocab_bpe', default="tokenizations/vocab.bpe", type=str, help="BPE vocab.bpe 路径")

    args = parser.parse_args()
    print('参数配置:\n' + repr(args))

    # 根据是否按词切分选择 tokenizer
    if args.segment:
        from tokenizations import tokenization_bert_word_level as tokenization_bert
    else:
        from tokenizations import tokenization_bert

    # 设置可见 GPU
    os.environ["CUDA_VISIBLE_DEVICES"] = args.device

    # 加载模型配置
    model_config = transformers.modeling_gpt2.GPT2Config.from_json_file(args.model_config)
    print('模型配置:\n' + model_config.to_json_string())

    n_ctx = model_config.n_ctx  # 上下文长度

    # 初始化 tokenizer
    if args.bpe_token:
        full_tokenizer = get_encoder(args.encoder_json, args.vocab_bpe)
    else:
        full_tokenizer = tokenization_bert.BertTokenizer(vocab_file=args.tokenizer_path)
    full_tokenizer.max_len = 999999  # 避免警告

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print('使用设备:', device)

    # 解析参数
    raw_data_path = args.raw_data_path
    tokenized_data_path = args.tokenized_data_path
    raw = args.raw
    epochs = args.epochs
    batch_size = args.batch_size
    lr = args.lr
    warmup_steps = args.warmup_steps
    log_step = args.log_step
    stride = args.stride
    gradient_accumulation = args.gradient_accumulation
    fp16 = args.fp16
    fp16_opt_level = args.fp16_opt_level
    max_grad_norm = args.max_grad_norm
    num_pieces = args.num_pieces
    min_length = args.min_length
    output_dir = args.output_dir
    tb_writer = SummaryWriter(log_dir=args.writer_dir)

    # 检查 log_step 是否为 gradient_accumulation 的整数倍
    assert log_step % gradient_accumulation == 0

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # 如果需要，先构建 tokenized 数据
    if raw:
        print('正在构建 tokenized 文件...')
        build_files(
            data_path=raw_data_path,
            tokenized_data_path=tokenized_data_path,
            num_pieces=num_pieces,
            full_tokenizer=full_tokenizer,
            min_length=min_length
        )
        print('文件构建完成')

    # 加载或初始化模型
    if not args.pretrained_model:
        model = transformers.modeling_gpt2.GPT2LMHeadModel(config=model_config)
    else:
        model = transformers.modeling_gpt2.GPT2LMHeadModel.from_pretrained(args.pretrained_model)
    model.train()
    model.to(device)

    # 打印模型参数量
    num_parameters = sum(p.numel() for p in model.parameters())
    print(f'模型参数总量: {num_parameters}')

    multi_gpu = False
    full_len = 0

    # 计算总训练步数
    print('正在计算总训练步数...')
    for i in tqdm(range(num_pieces)):
        with open(os.path.join(tokenized_data_path, f'tokenized_train_{i}.txt'), 'r') as f:
            full_len += len([int(item) for item in f.read().strip().split()])
    total_steps = int(full_len / stride * epochs / batch_size / gradient_accumulation)
    print(f'总训练步数 = {total_steps}')

    # 优化器与学习率调度器
    optimizer = transformers.AdamW(model.parameters(), lr=lr, correct_bias=True)
    scheduler = transformers.get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    # FP16 混合精度训练（需安装 NVIDIA Apex）
    if fp16:
        try:
            from apex import amp
        except ImportError:
            raise ImportError("请从 https://github.com/nvidia/apex 安装 apex 以启用 FP16 训练。")
        model, optimizer = amp.initialize(model, optimizer, opt_level=fp16_opt_level)

    # 多 GPU 支持
    if torch.cuda.device_count() > 1:
        print(f"使用 {torch.cuda.device_count()} 个 GPU 进行训练！")
        model = DataParallel(model, device_ids=[int(i) for i in args.device.split(',')])
        multi_gpu = True

    print('开始训练...')
    overall_step = 0
    running_loss = 0

    for epoch in range(epochs):
        print(f'第 {epoch + 1} 轮训练')
        now = datetime.now()
        print('当前时间:', now)

        # 随机打乱数据块顺序
        piece_indices = list(range(num_pieces))
        random.shuffle(piece_indices)
        piece_num = 0

        for i in piece_indices:
            # 读取一个分片的 tokenized 数据
            with open(os.path.join(tokenized_data_path, f'tokenized_train_{i}.txt'), 'r') as f:
                line = f.read().strip()
            tokens = [int(token) for token in line.split()]

            # 滑动窗口生成样本
            samples = []
            start_point = 0
            while start_point < len(tokens) - n_ctx:
                samples.append(tokens[start_point: start_point + n_ctx])
                start_point += stride
            if start_point < len(tokens):
                samples.append(tokens[-n_ctx:])  # 补齐最后一段

            random.shuffle(samples)

            # 按 batch 训练
            for step in range(len(samples) // batch_size):  # 丢弃不足一个 batch 的尾部
                batch = samples[step * batch_size: (step + 1) * batch_size]
                batch_inputs = torch.tensor(batch, dtype=torch.long).to(device)

                # 前向传播
                outputs = model(input_ids=batch_inputs, labels=batch_inputs)
                loss = outputs.loss

                # 多卡平均 loss
                if multi_gpu:
                    loss = loss.mean()

                # 梯度累积
                if gradient_accumulation > 1:
                    loss = loss / gradient_accumulation

                # 反向传播
                if fp16:
                    with amp.scale_loss(loss, optimizer) as scaled_loss:
                        scaled_loss.backward()
                    torch.nn.utils.clip_grad_norm_(amp.master_params(optimizer), max_grad_norm)
                else:
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)

                # 优化器更新
                if (overall_step + 1) % gradient_accumulation == 0:
                    running_loss += loss.item()
                    optimizer.step()
                    optimizer.zero_grad()
                    scheduler.step()

                # 记录日志
                if (overall_step + 1) % log_step == 0:
                    tb_writer.add_scalar('loss', loss.item() * gradient_accumulation, overall_step)
                    avg_loss = running_loss * gradient_accumulation / (log_step / gradient_accumulation)
                    print(f'当前时间: {datetime.now().hour}:{datetime.now().minute}. '
                          f'第 {step + 1} 步 / 第 {piece_num} 块 / 第 {epoch + 1} 轮, loss: {avg_loss:.4f}')
                    running_loss = 0

                overall_step += 1

            piece_num += 1

        # 保存每轮模型
        print(f'保存第 {epoch + 1} 轮模型')
        epoch_output_dir = os.path.join(output_dir, f'model_epoch{epoch + 1}')
        if not os.path.exists(epoch_output_dir):
            os.mkdir(epoch_output_dir)
        model_to_save = model.module if hasattr(model, 'module') else model
        model_to_save.save_pretrained(epoch_output_dir)
        print(f'第 {epoch + 1} 轮训练完成')

        then = datetime.now()
        print('结束时间:', then)
        print('本轮耗时:', then - now)

    print('训练完成！')
    final_output_dir = os.path.join(output_dir, 'final_model')
    if not os.path.exists(final_output_dir):
        os.mkdir(final_output_dir)
    model_to_save = model.module if hasattr(model, 'module') else model
    model_to_save.save_pretrained(final_output_dir)


if __name__ == '__main__':
    main()
