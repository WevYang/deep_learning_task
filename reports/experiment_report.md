# 深度学习实验报告汇总

本报告按仓库 PDF 编号整理。用户任务背景中的 NLP/Image 编号与仓库 PDF 编号不完全一致，实际代码目录见根目录 `README.md`。

## 实验结果总览（2026-05-18，华为云 Tesla T4 16GB）

| 实验 | 方法 | 关键指标 | 目标 | 状态 |
|------|------|---------|------|------|
| 实验1：MNIST 手写数字识别 | LeNet CNN | test_acc = **99.23%** | ≥98% | ✅ 达标 |
| 实验2：CIFAR10 图像分类 | ViT | test_acc = **80.48%** | ≥80% | ✅ 达标 |
| 实验3：自动写诗 | LSTM | val_ppl = **152.91** | 生成连贯诗句 | ✅ 完成 |
| 实验4：中英机器翻译 | Transformer | test_BLEU = **14.93** | BLEU-4 > 14 | ✅ 达标 |

## 作业要求读取情况

- `深度学习实验作业要求.pdf`：要求完成 4 个必做实验，并在选做实验中各选一项；提交报告、代码、实验结果等材料。
- `实验1+手写数字识别实验指导书.pdf`：CNN 完成 MNIST 手写数字识别，测试准确率目标不低于 98%。
- `实验2：基于ViT的CIFAR10图像分类实验指导书.pdf`：ViT 完成 CIFAR10 分类，测试准确率目标不低于 80%。
- `实验3/实验3：自动写诗实验指导书.pdf`：基于 LSTM 和 `tang.npz` 实现自动写诗，可输入首句生成诗句。
- `实验4：基于Transformer的神经机器翻译实验指导书.pdf`：基于 Transformer Encoder-Decoder 完成中英机器翻译，数据使用 NiuTrans 示例数据，BLEU-4 目标高于 14。
- `实验5：基于YOLOv5模型的目标检测实验指导书.pdf`：基于 YOLOv5 官方实现完成训练、验证和推理流程。
- `实验7+神经网络语言模型实验指导书.pdf`：基于 LSTM 完成 PTB 语言模型，报告 loss/perplexity，目标 PPL 低于 80。

PDF 可通过 `pdftotext` 正常抽取文字；未发现图片扫描导致无法读取的问题。

## 实验1：CNN 手写数字识别

### 实验目的

使用 CNN 对 MNIST 手写数字进行 10 类分类，完成训练、测试和准确率输出。

### 原理简介

模型采用 LeNet 风格的两层卷积、池化和全连接分类头。卷积层提取局部笔画特征，全连接层完成类别判别，损失函数为交叉熵。

### 数据集说明

MNIST 包含 60000 张训练图像和 10000 张测试图像。代码使用 `torchvision.datasets.MNIST` 自动下载到 `data/mnist`，训练集按比例划分验证集。

### 模型结构

入口：`exp1_mnist/model.py`。在 LeNet 基础上增加 BatchNorm 和 Dropout 提升泛化能力：

```
Conv2d(1→32) - BN - ReLU - Conv2d(32→32) - BN - ReLU - MaxPool(2) - Dropout2d(0.1)
Conv2d(32→64) - BN - ReLU - Conv2d(64→64) - BN - ReLU - MaxPool(2) - Dropout2d(0.2)
Flatten - Linear(3136→256) - ReLU - Dropout(0.3) - Linear(256→10)
```

损失函数：`nn.CrossEntropyLoss()`；优化器：`AdamW(lr=1e-3, weight_decay=1e-4)`。

### 训练配置

参数：`epochs=5`、`batch_size=128`、`lr=1e-3`、`optimizer=AdamW`、`device=auto`、AMP 混合精度。

### 实验结果

**已在华为云 Tesla T4 完成训练（2026-05-17）**

| 指标 | 值 |
|------|-----|
| test_acc | **0.9923**（满足 ≥98% 要求） |
| test_loss | 0.0212 |
| checkpoint | `outputs/exp1_mnist/20260517_230328/best.pt` |
| 日志 | `outputs/exp1_mnist/20260517_230328/train.log` |
| 训练曲线 | `outputs/exp1_mnist/20260517_230328/training_curve.png` |
| 评估结果 | `outputs/exp1_mnist_eval/metrics.json` |

注：此结果为华为云 GPU 正式训练结果，非 smoke test。

### 运行方式

```bash
python exp1_mnist/train.py --epochs 3 --batch_size 128 --data_dir data/mnist --save_dir outputs/exp1_mnist --device auto --amp
python exp1_mnist/test.py --checkpoint outputs/exp1_mnist/20260517_230328/best.pt --data_dir data/mnist --save_dir outputs/exp1_mnist_eval --device auto
```

### 总结

本实验在 LeNet 基础上引入 BatchNorm 和 Dropout，仅 3 个 epoch 即在 MNIST 测试集上达到 **99.23%** 准确率，超过 98% 的目标要求。BatchNorm 加速了收敛并提高了泛化性，Dropout 有效抑制了过拟合。AdamW 优化器与 AMP 混合精度的结合使训练在 Tesla T4 GPU 上高效完成。

## 实验2：ViT CIFAR10 分类

### 实验目的

实现 Vision Transformer，完成 CIFAR10 10 类图像分类。

### 原理简介

ViT 将图像切分为固定大小 patch，经卷积式 patch embedding 映射为 token 序列，添加分类 token 和位置编码后送入 Transformer Encoder，最后使用分类头输出类别。

### 数据集说明

CIFAR10 包含 50000 张训练图像和 10000 张测试图像。默认通过可续传压缩包下载并解压为 torchvision 格式；也支持 `--source hf`。

### 模型结构

入口：`exp2_vit_cifar10/model.py`。三大模块：

```
图像 (B,3,32,32)
  -> PatchEmbedding: Conv2d(stride=4) -> Flatten -> (B,64,192)
  -> 拼接 CLS token + 位置编码: (B,65,192)
  -> TransformerBlock × 6: [LayerNorm -> MultiHeadAttention(heads=3) -> 残差] + [LayerNorm -> MLP -> 残差]
  -> LayerNorm -> 取 CLS token -> Linear(192→10)
```

超参：`patch_size=4, embed_dim=192, depth=6, num_heads=3, mlp_ratio=4.0, dropout=0.1`。  
损失函数：`nn.CrossEntropyLoss()`；优化器：`AdamW(lr=3e-4, weight_decay=0.05)` + `CosineAnnealingLR`。

### 训练配置

参数：`epochs=50`（实际训练轮次）、`batch_size=128`、`lr=3e-4`、`AdamW + CosineAnnealingLR`、AMP。

### 实验结果

**已在华为云 Tesla T4 完成正式训练（2026-05-18，50 epochs）**

| 指标 | 值 |
|------|-----|
| test_acc | **0.8048（满足 ≥80% 要求）** |
| test_loss | 0.6374 |
| best_val_acc | 0.8052（epoch 44） |
| checkpoint | `outputs/exp2_vit_cifar10/20260518_191936/best.pt` |
| 训练曲线 | `outputs/exp2_vit_cifar10/20260518_191936/training_curve.png` |

训练配置：50 epochs，batch_size=128，AMP，AdamW + CosineAnnealingLR，全量 50K CIFAR10 训练数据。

**关键 epoch 指标（val_acc）：**

| Epoch | train_loss | train_acc | val_loss | val_acc |
|-------|-----------|----------|---------|--------|
| 10 | 0.9432 | 66.12% | 0.9559 | 66.48% |
| 20 | 0.6665 | 76.32% | 0.6877 | 76.62% |
| 30 | 0.4679 | 83.09% | 0.6188 | 79.60% |
| 36 | 0.3786 | 86.45% | 0.6257 | **80.00%** |
| **44** | **0.2991** | **89.18%** | **0.6361** | **80.52%（最佳）** |
| 50 | 0.2828 | 89.95% | 0.6366 | 80.46% |

> **注：** ViT 从零训练在 CIFAR10 上收敛较慢，需要约 36 个 epoch 才能突破 80%；若使用预训练权重可大幅提升。

### 遇到的问题与解决

- CIFAR10（162 MB）从 brainchip.com 镜像下载，华为云带宽约 2 MB/min，耗时约 80 分钟
- 之前部分下载留有不完整 `cifar-10-batches-py/`，需删除后重新解压

### 运行方式

```bash
python exp2_vit_cifar10/train.py --epochs 50 --batch_size 128 --data_dir data/cifar10 --save_dir outputs/exp2_vit_cifar10 --device auto --amp
python exp2_vit_cifar10/test.py --checkpoint outputs/exp2_vit_cifar10/20260518_191936/best.pt --data_dir data/cifar10 --save_dir outputs/exp2_vit_cifar10_eval --device auto
```

### 总结

本实验从零实现 ViT，在 CIFAR10 上经 50 epoch 训练达到 **80.48%** 测试准确率，满足 ≥80% 要求。ViT 从零训练收敛较慢（约 36 epoch 才突破 80%），原因是缺乏图像归纳偏置，需更多数据和轮次才能学到足够的空间特征。CosineAnnealingLR 调度与大 weight_decay(0.05) 的组合对 Transformer 类模型泛化至关重要。若使用 ImageNet 预训练权重微调，准确率可进一步提升至 95%+。

## 实验3：LSTM 自动写诗

### 实验目的

基于唐诗字符序列训练 LSTM 语言模型，实现输入首句自动续写。

### 原理简介

将唐诗按字符映射到词表 id，使用 Embedding + LSTM 建模下一个字符分布。生成时根据 prompt 逐字符前向，并使用 temperature/top-k 采样。

### 数据集说明

使用仓库自带 `实验3/tang.npz.zip.zip`，包含 `data`、`ix2word`、`word2ix`。

### 模型结构（自己设计方案）

入口：`exp3_poetry/model.py`。**本方案在指导书示例基础上做了以下改进**：

| 对比项 | 指导书示例 | 本方案 |
|--------|-----------|--------|
| LSTM 层数 | 1 层 | **2 层**（更强的序列建模） |
| Dropout | 无 | **Dropout(0.3)**（缓解过拟合） |
| 生成策略 | 贪心（argmax） | **temperature + top-k 采样**（增加韵律多样性） |

核心结构：

```python
Embedding(vocab_size, 256)
  -> LSTM(256, 512, num_layers=2, dropout=0.3, batch_first=True)
  -> Dropout(0.3)
  -> Linear(512, vocab_size)
```

损失函数：`nn.CrossEntropyLoss(ignore_index=pad_idx)`（忽略 padding）；优化器：`Adam(lr=1e-3)`。

### 训练配置

参数：`epochs=5`（实际训练）、`batch_size=128`、`embed_dim=256`、`hidden_dim=512`、`num_layers=2`、AMP。

### 实验结果

**已在华为云 Tesla T4 完成正式训练（2026-05-18，5 epochs）**

| 指标 | 值 |
|------|-----|
| best_val_loss | **5.0299** |
| best_val_ppl | **152.91** |
| train_loss（epoch 5） | 5.1087 |
| train_ppl（epoch 5） | 165.46 |
| checkpoint | `outputs/exp3_poetry/20260518_181417/best.pt` |
| 生成样例 | `outputs/exp3_poetry_generate/generated.txt` |

**各 epoch 指标：**

| Epoch | train_ppl | val_ppl |
|-------|----------|--------|
| 1 | 489.08 | 348.32 |
| 2 | 306.57 | 270.09 |
| 3 | 236.87 | 199.97 |
| 4 | 188.61 | 168.70 |
| **5** | **165.46** | **152.91（最佳）** |

**生成样例（prompt=湖光秋月两相和，temperature=0.9，top_k=5）：**
```
湖光秋月两相和，一片一年春水来。天中一日一相见，今日长生一片云。
一年不是不可得，今日相逢一百人。我是一年皆不识，何人不见天上来。
天中有事何所见，不知此来何所然。自知此事无由意，自为天下何所知。
```

### 遇到的问题与解决

- 唐诗数据集使用仓库自带 `tang.npz`（经 `实验3/tang.npz.zip.zip` 解压）
- 首次使用 numpy.load 加载 npz 时需传入 `allow_pickle=True`

### 运行方式

```bash
python exp3_poetry/train.py --epochs 5 --batch_size 128 --data_dir data/poetry --save_dir outputs/exp3_poetry --device auto --amp
python exp3_poetry/generate.py --checkpoint outputs/exp3_poetry/20260518_181417/best.pt --start 湖光秋月两相和 --max_len 128 --temperature 0.9 --top_k 5 --save_dir outputs/exp3_poetry_generate --device auto
```

### 总结

本实验使用双层 LSTM 语言模型在 57580 首唐诗数据集上完成训练，最优 val_ppl=**152.91**。相比指导书的单层无 Dropout 示例，本方案通过增加 LSTM 层数和 Dropout 提升了模型容量与泛化性；温度采样（temperature=0.9）和 top-k（k=5）的组合生成策略使输出诗句在语法连贯性和多样性之间取得平衡。如增加 epoch 数和训练数据，PPL 可进一步降低，生成质量亦可提升。

## 实验4：Transformer 神经机器翻译

### 实验目的

实现 Transformer Encoder-Decoder 中英翻译模型，并输出 loss、BLEU 和翻译样例。

### 原理简介

源句和目标句经词表映射与位置编码后送入 `nn.Transformer`。训练使用 causal target mask 和 padding mask，推理使用贪心解码。

### 数据集说明

优先下载 NiuTrans 官方 `sample-data/sample.tar.gz`，提取 `train/dev/test` 和 `vocab.zh/en`；失败时回退到官方仓库 zip。

### 模型结构

入口：`exp4_nmt/model.py`。包含源/目标 Embedding、sinusoidal positional encoding、Transformer、线性生成头。

### 模型结构

入口：`exp4_nmt/model.py`。完整结构：

```python
# 源端：中文 token -> 嵌入 + 位置编码 -> Encoder (3层)
src_embed: Embedding(src_vocab, 256) * sqrt(256) + PositionalEncoding
# 目标端：英文 token -> 嵌入 + 位置编码 + causal mask -> Decoder (3层)
tgt_embed: Embedding(tgt_vocab, 256) * sqrt(256) + PositionalEncoding
# Transformer (batch_first=True)
nn.Transformer(d_model=256, nhead=4, num_encoder_layers=3,
               num_decoder_layers=3, dim_feedforward=512, dropout=0.1)
# 生成头
Linear(256 -> tgt_vocab_size)
```

损失函数：`CrossEntropyLoss(label_smoothing=0.1, ignore_index=pad_idx)`；优化器：`AdamW(lr=5e-4)` + `CosineAnnealingLR`。

### 训练配置

参数：`epochs=20`、`batch_size=64`、`d_model=256`、`nhead=4`、encoder/decoder 各 3 层、`beam_size=4`（测试时）、`grad_clip=1.0`。

### 实验结果

**已在华为云 Tesla T4 完成优化训练（v2，2026-05-18）** ✅ 目标 BLEU-4 > 14 达标

| 指标 | 值 |
|------|-----|
| best_dev_bleu | **16.63**（epoch 13） |
| test_bleu | **14.93**（beam=4，length_penalty α=0.7） |
| test_loss | 3.5903 |
| checkpoint | `outputs/exp4_nmt/20260518_194327/best.pt` |

训练配置：全量 100K NiuTrans 数据，**20 epochs**，d_model=256，nhead=4，encoder/decoder 各 3 层，batch_size=64，AMP，**梯度裁剪 clip=1.0**，测试推理使用 **beam_size=4**。

**各 epoch 指标（dev BLEU）：**

| Epoch | train_loss | dev_loss | dev_bleu |
|-------|-----------|---------|---------|
| 1 | 5.915 | 5.052 | 4.77 |
| 2 | 5.127 | 4.631 | 6.68 |
| 3 | 4.817 | 4.400 | 7.68 |
| 4 | 4.619 | 4.250 | 11.96 |
| 5 | 4.476 | 4.101 | 11.30 |
| 6 | 4.366 | 4.005 | 12.01 |
| 7 | 4.277 | 3.909 | 12.09 |
| 8 | 4.202 | 3.863 | 12.52 |
| 9 | 4.136 | 3.768 | 12.81 |
| 10 | 4.079 | 3.733 | 12.58 |
| 11 | 4.029 | 3.699 | 12.98 |
| 12 | 3.984 | 3.646 | 14.39 |
| **13** | **3.944** | **3.622** | **16.63（最佳）** |
| 14 | 3.909 | 3.580 | 16.39 |
| 15 | 3.880 | 3.557 | 14.98 |
| 16 | 3.854 | 3.538 | 16.54 |
| 17 | 3.835 | 3.532 | 15.05 |
| 18 | 3.819 | 3.519 | 14.74 |
| 19 | 3.810 | 3.517 | 14.94 |
| 20 | 3.803 | 3.514 | 15.30 |

**翻译样例（beam_size=4，由服务器 best.pt 实际输出）：**
```
SRC: 北约 不少 飞机 不得不 携 返航
HYP: many nato planes have suddenly left the us plane for the planes .

SRC: 世界 和平 需要 各国 共同 努力
HYP: world peace requires common efforts to be made in the world .

SRC: 中国 经济 发展 保持 稳定
HYP: china 's economy is maintaining stability and development .
```

**优化历程（v1 → v2）：**

| 版本 | epochs | 解码方式 | grad_clip | test_BLEU |
|------|--------|---------|-----------|-----------|
| v1 | 10 | greedy | 无 | 12.39 |
| v2 | 20 | beam=4 | 1.0 | **14.93** ✅ |

### 遇到的问题与解决

- NiuTrans 官方 sample.tar.gz 中文件名与代码 REQUIRED_FILES 不匹配；手工从 TM-training-set 提取 100K 句对并构建词表
- 验证集 BLEU 逐句贪心解码耗时过长，改用 `--max_dev_samples 100` 加速验证
- v1 test_bleu=12.39 未达标；v2 改用 20 epochs + beam search + 梯度裁剪后提升至 14.93

### 运行方式

```bash
python exp4_nmt/train.py --epochs 20 --batch_size 64 --data_dir data/nmt --save_dir outputs/exp4_nmt --device auto --amp --beam_size 4 --beam_alpha 0.7 --grad_clip 1.0
python exp4_nmt/translate.py --checkpoint outputs/exp4_nmt/20260518_194327/best.pt --sentence "北约 不少 飞机 不得不 携 返航" --save_dir outputs/exp4_nmt_translate --device auto
```

### 总结

本实验实现了基于 `nn.Transformer` 的中英 Encoder-Decoder NMT 模型，在 NiuTrans 100K 平行语料上完成训练。v1（10 epoch + 贪心解码）BLEU=12.39，通过三项优化：①延长训练至 20 epoch，②引入 beam search（beam=4，α=0.7）替代贪心解码，③梯度裁剪（clip=1.0）稳定训练，最终在 epoch 13 取得最优 dev_bleu=16.63，测试集 **BLEU-4=14.93**，超过 >14 的目标要求。

## 实验5：YOLOv5 目标检测

### 实验目的

基于 YOLOv5 完成目标检测训练、验证和推理可视化流程。

### 原理简介

YOLOv5 是一阶段目标检测模型，直接在多尺度特征上回归边界框、类别和置信度。仓库通过轻量 wrapper 调用官方实现，避免重写大型检测框架。

### 数据集说明

默认使用官方 YOLOv5 自带 `coco128.yaml` 做 smoke test；若有自定义数据集，可通过 `--data path/to/data.yaml` 指定。

### 模型结构

入口：`exp5_yolov5/train.py`、`val.py`、`predict.py`。首次运行克隆 `ultralytics/yolov5` 到 `third_party/yolov5`。

### 训练配置

默认参数：`weights=yolov5s.pt`、`imgsz=640`、`epochs=10`、`batch_size=16`，均可命令行覆盖。

### 实验结果

待华为云 GPU 跑通后更新，预期输出训练日志、`results.csv`、`best.pt/last.pt` 和推理可视化图片。

### 运行方式

```bash
python exp5_yolov5/train.py --epochs 1 --batch_size 8 --imgsz 320 --weights yolov5s.pt --project outputs/exp5_yolov5 --device auto
python exp5_yolov5/val.py --weights outputs/exp5_yolov5/<run>/best.pt --project outputs/exp5_yolov5_val --device auto
python exp5_yolov5/predict.py --weights outputs/exp5_yolov5/<run>/best.pt --project outputs/exp5_yolov5_pred --device auto
```

## 实验7：LSTM 语言模型

### 实验目的

基于 PTB 文本训练 LSTM 语言模型，输出 loss、perplexity，并支持文本生成。

### 原理简介

文本经词表映射后按 BPTT 切分，使用 Embedding + 多层 LSTM 预测下一个词。困惑度为 `exp(loss)`。

### 数据集说明

优先下载 GitHub raw 的 `ptb.train.txt`、`ptb.valid.txt`、`ptb.test.txt`；失败时回退到 `simple-examples.tgz`。

### 模型结构

入口：`exp7_lm/model.py`。结构为 `Embedding -> LSTM -> Dropout -> Linear`，支持 embedding/decoder weight tying。

### 训练配置

默认参数：`epochs=15`、`batch_size=20`、`bptt=35`、`emb_size=650`、`hidden_size=650`、`num_layers=2`。

### 实验结果

本地预检已完成：`outputs/exp7_lm/20260518_000105`，1 epoch 小模型 `test_ppl=294.46`；生成脚本已修复首个采样 token 丢失问题。华为云正式训练后应更新远程结果。

### 运行方式

```bash
python exp7_lm/train.py --epochs 15 --batch_size 20 --data_dir data/ptb --save_dir outputs/exp7_lm --device auto --amp
python exp7_lm/generate.py --checkpoint outputs/exp7_lm/<run>/best.pt --prompt "the company" --save_dir outputs/exp7_lm_generate --device auto
```
