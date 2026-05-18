# 模型权重说明

| 文件 | 实验 | val指标 | 说明 |
|------|------|---------|------|
| exp1_mnist_best.pt | 实验一 CNN MNIST | val_acc=99.02% | 本地实际训练，test_acc=99.23% |
| exp2_vit_cifar10_best.pt | 实验二 ViT CIFAR10 | val_acc=80.52% | 华为云服务器训练（50 epoch） |
| exp3_poetry_best.pt | 实验三 LSTM 写诗 | val_ppl=152.91 | 华为云服务器训练（8 epoch） |
| exp4_nmt_best.pt | 实验四 Transformer NMT | dev_bleu=16.63 | 华为云服务器训练（20 epoch） |

> 注：exp2/exp3/exp4 权重文件在华为云服务器 120.46.139.122 的
> `~/rivermind-data/deep_learning/deep_learning_task/outputs/` 目录下，
> 因文件较大（16MB~50MB）暂未上传至 GitHub，可按需传输。
