# deep_learning_task

本仓库已按 PDF 实验指导书补全 6 个实验的可运行代码、命令行入口、数据准备、日志与报告输出逻辑。

注意：仓库 PDF 编号与用户任务背景编号不完全一致。当前目录按 PDF 文件编号组织：

| PDF 编号 | 任务 | 目录 |
| --- | --- | --- |
| 实验1 | CNN 手写数字识别 MNIST | `exp1_mnist/` |
| 实验2 | ViT CIFAR10 图像分类 | `exp2_vit_cifar10/` |
| 实验3 | LSTM 自动写诗 | `exp3_poetry/` |
| 实验4 | Transformer 神经机器翻译 | `exp4_nmt/` |
| 实验5 | YOLOv5 目标检测 | `exp5_yolov5/` |
| 实验7 | LSTM 语言模型 PTB | `exp7_lm/` |

用户任务中的必做项对应：自动写诗、机器翻译、MNIST、CIFAR10；选做项选择了 LSTM Language Model 和 YOLOv5。

## 环境

```bash
cd ~/rivermind-data/deep_learning/deep_learning_task
python -m pip install -r requirements.txt
python - <<'PY'
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
PY
```

所有训练入口均支持 `--device auto`，CUDA 可用时自动使用 GPU，否则降级到 CPU。

## 数据

- MNIST：`torchvision.datasets.MNIST` 自动下载到 `data/mnist`。
- CIFAR10：默认使用可续传压缩包下载并按 torchvision 格式解压到 `data/cifar10`；可选 `--source hf` 使用 Hugging Face 数据集。
- 唐诗：优先读取仓库自带 `实验3/tang.npz.zip.zip`，并解压到 `data/poetry`。
- NiuTrans：优先下载官方 `sample-data/sample.tar.gz`，失败时回退到仓库 zip。
- PTB：优先下载 `ptb.train/valid/test.txt` 原始文本，失败时回退到 Mikolov `simple-examples.tgz`。
- YOLOv5：首次运行时克隆官方 `ultralytics/yolov5` 到 `third_party/yolov5`，默认使用其 `coco128.yaml` 做 smoke/full 流程。

`data/`、`outputs/`、`third_party/` 和大权重均已在 `.gitignore` 中忽略。

## 运行命令

### 实验1 MNIST

```bash
python exp1_mnist/train.py --epochs 3 --batch_size 128 --data_dir data/mnist --save_dir outputs/exp1_mnist --device auto --amp
python exp1_mnist/test.py --checkpoint outputs/exp1_mnist/<run>/best.pt --data_dir data/mnist --save_dir outputs/exp1_mnist_eval --device auto
```

### 实验2 ViT CIFAR10

```bash
python exp2_vit_cifar10/train.py --epochs 20 --batch_size 128 --data_dir data/cifar10 --save_dir outputs/exp2_vit_cifar10 --device auto --amp
python exp2_vit_cifar10/test.py --checkpoint outputs/exp2_vit_cifar10/<run>/best.pt --data_dir data/cifar10 --save_dir outputs/exp2_vit_cifar10_eval --device auto
```

快速验证可加：

```bash
--max_train_samples 2000 --max_test_samples 1000
```

### 实验3 LSTM 自动写诗

```bash
python exp3_poetry/train.py --epochs 8 --batch_size 128 --data_dir data/poetry --save_dir outputs/exp3_poetry --device auto --amp
python exp3_poetry/generate.py --checkpoint outputs/exp3_poetry/<run>/best.pt --start 湖光秋月两相和 --save_dir outputs/exp3_poetry_generate --device auto
```

### 实验4 Transformer NMT

```bash
python exp4_nmt/train.py --epochs 10 --batch_size 64 --data_dir data/nmt --save_dir outputs/exp4_nmt --device auto --amp
python exp4_nmt/translate.py --checkpoint outputs/exp4_nmt/<run>/best.pt --sentence "北约 不少 飞机 不得不 携 返航" --save_dir outputs/exp4_nmt_translate --device auto
```

快速验证可加：

```bash
--max_train_samples 300 --max_dev_samples 50 --max_test_samples 50 --d_model 128 --num_encoder_layers 2 --num_decoder_layers 2 --dim_feedforward 256
```

### 实验5 YOLOv5

```bash
python exp5_yolov5/train.py --epochs 1 --batch_size 8 --imgsz 320 --weights yolov5s.pt --project outputs/exp5_yolov5 --device auto
python exp5_yolov5/val.py --weights outputs/exp5_yolov5/<run>/best.pt --project outputs/exp5_yolov5_val --device auto
python exp5_yolov5/predict.py --weights outputs/exp5_yolov5/<run>/best.pt --project outputs/exp5_yolov5_pred --device auto
```

### 实验7 LSTM Language Model

```bash
python exp7_lm/train.py --epochs 15 --batch_size 20 --data_dir data/ptb --save_dir outputs/exp7_lm --device auto --amp
python exp7_lm/generate.py --checkpoint outputs/exp7_lm/<run>/best.pt --prompt "the company" --save_dir outputs/exp7_lm_generate --device auto
```

## 报告

合并实验报告草稿在 `reports/experiment_report.md`。正式远程 GPU 训练完成后，将以 `outputs/<experiment>/<timestamp>/metrics.json`、`train.log`、曲线图、生成文本或预测图片更新报告结果段。
