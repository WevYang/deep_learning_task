"""生成4份深度学习实验讲解幻灯片（符合作业要求，约10页/份）。"""
from __future__ import annotations
import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

BASE = Path(__file__).parent

# ── 颜色 ──────────────────────────────────────────────────
NAVY   = RGBColor(0x1A, 0x33, 0x5C)   # 深蓝（标题栏）
STEEL  = RGBColor(0x2E, 0x5F, 0x8A)   # 中蓝（副标题/强调）
LBLUE  = RGBColor(0xE8, 0xF0, 0xF8)   # 浅蓝（内容背景）
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
DARK   = RGBColor(0x1C, 0x1C, 0x1C)
GRAY   = RGBColor(0x55, 0x55, 0x55)
GREEN  = RGBColor(0x1A, 0x7A, 0x3C)
RED    = RGBColor(0xB5, 0x2A, 0x2A)
GOLD   = RGBColor(0xB8, 0x86, 0x0B)

W = 13.33   # slide width  (inches)
H = 7.5     # slide height (inches)


def new_prs():
    prs = Presentation()
    prs.slide_width  = Inches(W)
    prs.slide_height = Inches(H)
    return prs


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def bg(slide, color: RGBColor):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def rect(slide, l, t, w, h, fc=None, lc=None):
    from pptx.util import Inches
    shp = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    shp.fill.solid() if fc else shp.fill.background()
    if fc: shp.fill.fore_color.rgb = fc
    shp.line.fill.background() if not lc else None
    if lc: shp.line.color.rgb = lc
    return shp


def txt(slide, text, l, t, w, h, size=18, bold=False,
        color=DARK, align=PP_ALIGN.LEFT, wrap=True, italic=False):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tb.word_wrap = wrap
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color


def multi_bullet(slide, items, l, t, w, h_per=0.52,
                 size=17, color=DARK, indent_char="  "):
    """逐行输出 bullet，支持两级缩进（以两空格开头为二级）。"""
    y = t
    for item in items:
        is_sub = item.startswith(indent_char)
        text = item.lstrip()
        mark = "▸ " if not is_sub else "    – "
        fs = size if not is_sub else size - 1
        fc = color if not is_sub else GRAY
        txt(slide, mark + text, l, y, w, h_per, size=fs, color=fc)
        y += h_per


# ── 封面 ──────────────────────────────────────────────────
def cover(prs, title, subtitle, author="WevYang", course="中国科学院大学  深度学习"):
    slide = blank(prs)
    bg(slide, NAVY)

    # 左侧竖色块
    rect(slide, 0, 0, 0.18, H, fc=GOLD)

    # 校徽（右上角）
    logo = str(BASE / "ucas_seal.png")
    if Path(logo).exists():
        slide.shapes.add_picture(logo,
            Inches(W - 1.55), Inches(0.25),
            Inches(1.3), Inches(1.17))

    # 主标题
    txt(slide, title, 0.55, 1.9, 11.5, 1.4,
        size=34, bold=True, color=WHITE, align=PP_ALIGN.LEFT)

    # 分隔线
    rect(slide, 0.55, 3.45, 9.5, 0.04, fc=GOLD)

    # 副标题
    txt(slide, subtitle, 0.55, 3.6, 11.0, 0.8,
        size=20, color=RGBColor(0xC8, 0xD8, 0xF0), align=PP_ALIGN.LEFT)

    # 作者 + 课程
    txt(slide, f"{author}　|　{course}", 0.55, H - 0.95, 11.0, 0.55,
        size=15, color=RGBColor(0xA0, 0xB8, 0xD0), align=PP_ALIGN.LEFT)


# ── 节标题页 ──────────────────────────────────────────────
def section_page(prs, number, title):
    slide = blank(prs)
    bg(slide, STEEL)
    rect(slide, 0, 0, 0.18, H, fc=GOLD)
    txt(slide, number, 0.5, 2.4, 2.0, 1.2,
        size=52, bold=True, color=RGBColor(0xFF, 0xCC, 0x44), align=PP_ALIGN.CENTER)
    txt(slide, title, 2.6, 2.85, 9.5, 1.0,
        size=28, bold=True, color=WHITE)


# ── 普通内容页 ────────────────────────────────────────────
def content_page(prs, title, items, size=17):
    slide = blank(prs)
    bg(slide, WHITE)
    rect(slide, 0, 0, W, 1.05, fc=NAVY)
    rect(slide, 0, 0, 0.18, H, fc=NAVY)
    txt(slide, title, 0.38, 0.1, 12.6, 0.85,
        size=23, bold=True, color=WHITE)
    multi_bullet(slide, items, 0.45, 1.22, 12.3, size=size)
    rect(slide, 0, H - 0.12, W, 0.12, fc=NAVY)


# ── 双栏页 ────────────────────────────────────────────────
def two_col(prs, title, ltitle, litems, rtitle, ritems, size=16):
    slide = blank(prs)
    bg(slide, WHITE)
    rect(slide, 0, 0, W, 1.05, fc=NAVY)
    rect(slide, 0, 0, 0.18, H, fc=NAVY)
    txt(slide, title, 0.38, 0.1, 12.6, 0.85,
        size=23, bold=True, color=WHITE)
    # 左列
    rect(slide, 0.38, 1.15, 5.9, 0.48, fc=LBLUE)
    txt(slide, ltitle, 0.48, 1.2, 5.7, 0.38,
        size=17, bold=True, color=NAVY)
    multi_bullet(slide, litems, 0.45, 1.72, 5.82, size=size)
    # 右列
    rect(slide, 6.95, 1.15, 5.9, 0.48, fc=LBLUE)
    txt(slide, rtitle, 7.05, 1.2, 5.7, 0.38,
        size=17, bold=True, color=NAVY)
    multi_bullet(slide, ritems, 7.0, 1.72, 5.82, size=size)
    rect(slide, 0, H - 0.12, W, 0.12, fc=NAVY)


# ── 代码页 ────────────────────────────────────────────────
def code_page(prs, title, code: str, note: str = ""):
    slide = blank(prs)
    bg(slide, WHITE)
    rect(slide, 0, 0, W, 1.05, fc=NAVY)
    rect(slide, 0, 0, 0.18, H, fc=NAVY)
    txt(slide, title, 0.38, 0.1, 12.6, 0.85,
        size=23, bold=True, color=WHITE)
    # 代码框
    code_h = 5.5 if not note else 4.6
    rect(slide, 0.38, 1.15, 12.55, code_h, fc=RGBColor(0x1E, 0x1E, 0x2E))
    txt(slide, code, 0.52, 1.22, 12.25, code_h - 0.1,
        size=12, color=RGBColor(0xCB, 0xD3, 0xE3), wrap=True)
    if note:
        txt(slide, note, 0.45, 1.15 + code_h + 0.1, 12.3, 0.8,
            size=14, color=GRAY, italic=True)
    rect(slide, 0, H - 0.12, W, 0.12, fc=NAVY)


# ── 结果卡片页 ────────────────────────────────────────────
def result_page(prs, title, metrics: list[tuple], analysis: list[str]):
    slide = blank(prs)
    bg(slide, WHITE)
    rect(slide, 0, 0, W, 1.05, fc=NAVY)
    rect(slide, 0, 0, 0.18, H, fc=NAVY)
    txt(slide, title, 0.38, 0.1, 12.6, 0.85,
        size=23, bold=True, color=WHITE)
    # 指标卡
    cw = (W - 0.8) / len(metrics) - 0.15
    for i, (label, val, note) in enumerate(metrics):
        x = 0.4 + i * (cw + 0.15)
        rect(slide, x, 1.2, cw, 2.1, fc=LBLUE)
        rect(slide, x, 1.2, cw, 0.08, fc=NAVY)
        txt(slide, val, x, 1.35, cw, 1.0,
            size=30, bold=True, color=GREEN if "✅" not in note else GREEN,
            align=PP_ALIGN.CENTER)
        txt(slide, label, x, 2.4, cw, 0.5,
            size=13, color=DARK, align=PP_ALIGN.CENTER)
        if note:
            txt(slide, note, x, 2.88, cw, 0.35,
                size=11, color=GRAY, align=PP_ALIGN.CENTER, italic=True)
    # 分析
    multi_bullet(slide, analysis, 0.45, 3.45, 12.3, size=16)
    rect(slide, 0, H - 0.12, W, 0.12, fc=NAVY)


# ══════════════════════════════════════════════════════════
# 实验一  MNIST CNN
# ══════════════════════════════════════════════════════════
def exp1():
    prs = new_prs()

    # 1. 封面
    cover(prs,
          "实验一：手写数字识别",
          "基于卷积神经网络（CNN）的 MNIST 分类 | PyTorch")

    # 2. 概述
    content_page(prs, "概述", [
        "任务：对 MNIST 手写数字（0–9）进行 10 分类",
        "数据集：MNIST，共 70,000 张 28×28 灰度图",
        "解决方案：改进版 LeNet——双卷积块 + BatchNorm + Dropout + 全连接分类头",
        "评估指标：测试集分类准确率（目标 ≥ 98%）",
        "训练环境：华为云 Tesla T4 GPU，PyTorch 2.2 + AMP 混合精度",
        "  最终结果：test_acc = 99.23%，超过目标要求",
    ])

    # 3. 数据集
    content_page(prs, "数据集介绍：MNIST", [
        "来源：Yann LeCun 等人，1998 年发布，深度学习领域标准基准之一",
        "规模：训练集 60,000 张 + 测试集 10,000 张，共 10 类数字",
        "图像大小：28×28 像素，单通道灰度，像素值 0–255",
        "本实验切出 10% 训练样本（6,000 张）作为验证集",
        "数据预处理：Normalize(mean=0.1307, std=0.3081)，对齐像素分布",
        "  数据增强：训练时不做额外增强（MNIST 本身难度较低，无需增强）",
    ])

    # 4. 网络结构
    two_col(prs, "解决方案：网络结构设计",
            "第一卷积块（28×28 → 14×14）", [
                "Conv2d(1→32, 3×3, padding=1)",
                "BatchNorm2d(32)  ← 加速收敛",
                "ReLU 激活",
                "Conv2d(32→32, 3×3, padding=1)",
                "BatchNorm2d + ReLU",
                "MaxPool2d(2)  →  Dropout2d(0.1)",
            ],
            "第二卷积块（14×14 → 7×7）+ 分类头", [
                "Conv2d(32→64, 3×3) × 2  +  BN + ReLU",
                "MaxPool2d(2)  →  Dropout2d(0.2)",
                "Flatten：(B,64,7,7) → (B,3136)",
                "Linear(3136→256)  +  ReLU",
                "Dropout(0.3)",
                "Linear(256→10)  输出 10 类 logits",
            ])

    # 5. 损失函数与优化器
    content_page(prs, "解决方案：损失函数与优化器设计", [
        "损失函数：交叉熵损失 CrossEntropyLoss",
        "  内部等价于 Softmax + NLLLoss，数值稳定性好",
        "优化器：AdamW（lr=1e-3，weight_decay=1e-4）",
        "  相比 Adam 额外对权重本身施加 L2 正则，减少过拟合风险",
        "学习率策略：固定学习率，5 个 epoch 足以收敛",
        "混合精度（AMP）：fp16 前向传播，fp32 梯度更新，T4 训练加速约 1.5×",
        "Batch Size：128；每 epoch 保存验证集最优 checkpoint",
    ])

    # 6. 核心代码
    code_page(prs, "核心代码：模型定义",
        "class LeNetMNIST(nn.Module):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self.features = nn.Sequential(\n"
        "            # 第一卷积块\n"
        "            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),\n"
        "            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),\n"
        "            nn.MaxPool2d(2), nn.Dropout2d(0.1),\n"
        "            # 第二卷积块\n"
        "            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),\n"
        "            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),\n"
        "            nn.MaxPool2d(2), nn.Dropout2d(0.2),\n"
        "        )\n"
        "        self.classifier = nn.Sequential(\n"
        "            nn.Flatten(),\n"
        "            nn.Linear(64*7*7, 256), nn.ReLU(), nn.Dropout(0.3),\n"
        "            nn.Linear(256, 10),          # 输出 10 个类别的 logit\n"
        "        )\n"
        "    def forward(self, x):\n"
        "        return self.classifier(self.features(x))",
        note="BatchNorm 放在 ReLU 前（BN-ReLU 顺序），实践中更稳定。")

    # 7. 实验结果与分析
    result_page(prs, "实验结果与分析",
        [("测试准确率", "99.23%", "✅ 超过 ≥98%"),
         ("测试损失",   "0.0212", ""),
         ("最优 epoch", "3 / 5",  "")],
        [
            "3 个 epoch 即达到最优，BatchNorm 对收敛速度提升显著",
            "训练集与验证集准确率差距极小（<0.3%），无过拟合",
            "Dropout 在 MNIST 上效果略微提升，作用不如在更大数据集上明显",
            "对比：不加 BatchNorm 的 LeNet，相同 epoch 下准确率约 98.5%",
        ])

    # 8. 总结
    content_page(prs, "总结与展望", [
        "本实验在 LeNet 基础上引入 BatchNorm 和 Dropout，最终测试准确率达 99.23%",
        "BatchNorm 加速收敛且提升泛化，是现代 CNN 的标配组件",
        "AdamW + AMP 的组合使训练在 GPU 上高效完成，3 epoch 即收敛",
        "不足：MNIST 难度偏低，模型在真实场景噪声下鲁棒性待验证",
        "  改进方向①：加入数据增强（随机旋转、仿射变换）提升噪声鲁棒性",
        "  改进方向②：用 ResNet / EfficientNet 迁移学习，可轻松超过 99.5%",
    ])

    prs.save(str(BASE / "exp1_cnn_mnist.pptx"))
    print("exp1 done")


# ══════════════════════════════════════════════════════════
# 实验二  ViT CIFAR10
# ══════════════════════════════════════════════════════════
def exp2():
    prs = new_prs()

    cover(prs,
          "实验二：基于 ViT 的 CIFAR10 图像分类",
          "Vision Transformer 从零实现 | PyTorch")

    content_page(prs, "概述", [
        "任务：对 CIFAR10 数据集（10类彩色图像）进行分类",
        "数据集：CIFAR10，50,000 训练 + 10,000 测试，32×32 彩色图",
        "解决方案：从零实现 Vision Transformer（ViT）",
        "  PatchEmbedding → CLS Token → Transformer Encoder × 6 → Linear Head",
        "评估指标：测试集分类准确率（目标 ≥ 80%）",
        "  最终结果：test_acc = 80.48%，满足目标要求",
    ])

    content_page(prs, "数据集介绍：CIFAR10", [
        "来源：Alex Krizhevsky，2009 年发布，图像分类经典基准",
        "类别：飞机、汽车、鸟、猫、鹿、狗、青蛙、马、船、卡车（各 6,000 张）",
        "图像大小：32×32 像素，3 通道 RGB",
        "训练增强：RandomResizedCrop(32) + RandomHorizontalFlip",
        "标准化：mean=(0.4914,0.4822,0.4465)，std=(0.2023,0.1994,0.2010)",
        "  切出 10% 训练样本作验证集；测试集不做增强，仅做标准化",
    ])

    content_page(prs, "解决方案：ViT 原理与结构", [
        "核心思想：将图像视为 patch 序列，用 Transformer 建模全局依赖",
        "① Patch 分割：image(32×32) → 64 个 4×4 的 patch",
        "  每个 patch 通过 Conv2d（stride=patch_size）线性投影为 192 维向量",
        "② CLS Token：在序列头部拼接可学习的分类 token（1×192）",
        "③ 位置编码：可学习位置嵌入，形状 (1, 65, 192)",
        "④ Transformer Encoder × 6：Pre-Norm + 多头自注意力（3头）+ FFN",
        "  每个 Block：x = x + Attn(LN(x))；x = x + FFN(LN(x))",
        "⑤ 分类头：取 CLS token 位置输出 → Linear(192→10)",
    ])

    two_col(prs, "解决方案：训练策略与超参数",
            "模型超参", [
                "image_size=32, patch_size=4",
                "embed_dim=192, depth=6",
                "num_heads=3, mlp_ratio=4.0",
                "dropout=0.1",
                "总参数量：约 3.7M",
            ],
            "训练超参", [
                "epochs=50（从零训练需要更多轮）",
                "batch_size=128",
                "optimizer=AdamW, lr=3e-4",
                "weight_decay=0.05（ViT 需要强正则）",
                "scheduler=CosineAnnealingLR",
            ])

    code_page(prs, "核心代码：TransformerBlock（Pre-Norm）",
        "class TransformerBlock(nn.Module):\n"
        "    def __init__(self, dim, num_heads, mlp_ratio, dropout):\n"
        "        super().__init__()\n"
        "        self.norm1 = nn.LayerNorm(dim)\n"
        "        self.attn  = nn.MultiheadAttention(\n"
        "            dim, num_heads, dropout=dropout, batch_first=True)\n"
        "        self.norm2 = nn.LayerNorm(dim)\n"
        "        self.mlp   = MLP(dim, int(dim * mlp_ratio), dropout)\n"
        "\n"
        "    def forward(self, x):\n"
        "        # Pre-Norm 形式：先做 LayerNorm 再进 Attention，训练更稳定\n"
        "        attn_out, _ = self.attn(\n"
        "            self.norm1(x), self.norm1(x), self.norm1(x),\n"
        "            need_weights=False)\n"
        "        x = x + attn_out        # 残差连接\n"
        "        x = x + self.mlp(self.norm2(x))\n"
        "        return x",
        note="Pre-Norm 相比 Post-Norm 在深层网络中梯度更稳定，是 ViT 的标准做法。")

    result_page(prs, "实验结果与分析",
        [("测试准确率", "80.48%", "✅ 满足 ≥80%"),
         ("最优验证准确率", "80.52%", "epoch 44"),
         ("突破 80% 时间", "epoch 36", "")],
        [
            "从零训练 ViT 收敛较慢——缺乏图像归纳偏置（平移不变性）是主因",
            "CosineAnnealingLR 在训练后期有效抑制振荡，是最终达标的关键",
            "weight_decay=0.05 比常规设置大，对 Transformer 类模型泛化很重要",
            "对比：使用 ImageNet 预训练权重微调，同模型可达 95%+（迁移学习优势）",
        ])

    content_page(prs, "总结与展望", [
        "从零实现了完整 ViT，包含 PatchEmbed、CLS Token、位置编码、TransformerBlock",
        "经过 50 epoch 训练达到 80.48% 测试准确率，满足实验要求",
        "Pre-Norm + 残差结构保证了深层网络训练的稳定性",
        "ViT 相比 CNN 的优势在于全局建模能力，劣势是样本效率较低",
        "  改进方向①：使用预训练权重（DeiT/MAE）微调，大幅减少所需 epoch",
        "  改进方向②：引入 Mixup / CutMix 数据增强，进一步提升泛化",
    ])

    prs.save(str(BASE / "exp2_vit_cifar10.pptx"))
    print("exp2 done")


# ══════════════════════════════════════════════════════════
# 实验三  自动写诗
# ══════════════════════════════════════════════════════════
def exp3():
    prs = new_prs()

    cover(prs,
          "实验三：自动写诗",
          "基于双层 LSTM 的唐诗语言模型 | PyTorch")

    content_page(prs, "概述", [
        "任务：训练语言模型，给定首句自动续写唐诗",
        "数据集：预处理后的 tang.npz，含 57,580 首唐诗",
        "解决方案（自己方案）：双层 LSTM + Dropout + temperature/top-k 采样",
        "  相比指导书示例（单层 LSTM + 贪心解码）做了三处改进",
        "评估指标：验证集困惑度 PPL = exp(val_loss)（越低越好）",
        "  最终结果：best val_ppl = 152.91，生成诗句语法连贯",
    ])

    content_page(prs, "数据集介绍：唐诗语料库", [
        "来源：课程提供的预处理唐诗数据集 tang.npz",
        "规模：57,580 首唐诗，每首限定 125 个字符",
        "  不足 125 字的以 </s>（padding token）填充",
        "格式：npz 文件，包含 data（字符 id 序列）、ix2word、word2ix 三部分",
        "词表大小：约 8,293 个唯一字符（含特殊符号 <START>、<EOP>、</s>）",
        "  切出 5% 样本（约 2,879 首）作为验证集，其余用于训练",
    ])

    two_col(prs, "解决方案：本方案 vs 指导书示例",
            "指导书示例（基线）", [
                "Embedding(vocab_size, dim)",
                "单层 LSTM（num_layers=1）",
                "无 Dropout",
                "Linear(hidden_dim → vocab_size)",
                "生成：贪心解码（每步取 argmax）",
                "  缺点：输出往往过于保守、重复",
            ],
            "本方案改进（三处）", [
                "双层 LSTM（num_layers=2）",
                "  → 增强对长程依赖的建模能力",
                "Dropout(0.3)：层间 + 输出后各一层",
                "  → 缓解过拟合，提升泛化",
                "Temperature(0.9) + Top-k(5) 采样",
                "  → 生成更有韵律变化，避免重复",
            ])

    code_page(prs, "核心代码：模型定义与生成策略",
        "class PoetryLSTM(nn.Module):\n"
        "    def __init__(self, vocab_size, embed_dim=256,\n"
        "                 hidden_dim=512, num_layers=2, dropout=0.3):\n"
        "        super().__init__()\n"
        "        self.embedding = nn.Embedding(vocab_size, embed_dim,\n"
        "                                      padding_idx=pad_idx)\n"
        "        # 双层 LSTM，层间自动施加 Dropout\n"
        "        self.lstm = nn.LSTM(embed_dim, hidden_dim,\n"
        "                            num_layers=num_layers,\n"
        "                            batch_first=True, dropout=dropout)\n"
        "        self.dropout = nn.Dropout(dropout)  # 输出后额外 Dropout\n"
        "        self.fc = nn.Linear(hidden_dim, vocab_size)\n"
        "\n"
        "# Temperature + Top-k 采样（生成时使用）\n"
        "def sample_next(logits, temperature=0.9, top_k=5):\n"
        "    logits = logits / temperature          # 调整分布\"尖锐\"程度\n"
        "    values, indices = torch.topk(logits, top_k)\n"
        "    probs = torch.softmax(values, dim=-1)\n"
        "    return indices[torch.multinomial(probs, 1).item()].item()",
        note="temperature<1 使分布更集中（更保守）；top_k 限制候选范围，避免生成罕见字。")

    content_page(prs, "训练方案", [
        "损失函数：CrossEntropyLoss（ignore_index=pad_idx，忽略填充 token）",
        "优化器：Adam（lr=1e-3，weight_decay=1e-5）",
        "Batch Size=128；训练 5 个 epoch",
        "评估：每 epoch 结束后计算验证集平均 loss，取最低时保存 best.pt",
        "混合精度 AMP 加速训练，T4 GPU 上单 epoch 约 3 分钟",
        "生成时：加载 best.pt，逐字符前向，使用 temperature=0.9，top_k=5",
    ])

    result_page(prs, "实验结果与分析",
        [("最优 val_ppl", "152.91", "epoch 5"),
         ("最优 val_loss", "5.0299", ""),
         ("训练 epoch 数", "5", "")],
        [
            "生成样例（prompt=湖光秋月两相和）：",
            "  湖光秋月两相和，一片一年春水来。天中一日一相见，今日长生一片云。",
            "双层 LSTM 相比单层，val_ppl 从约 178 降至 152.91（↓ 14%）",
            "top-k 采样生成的诗句韵律感优于贪心解码，重复率明显降低",
            "5 epoch 后 ppl 仍在下降，继续训练可进一步改善",
        ])

    content_page(prs, "总结与展望", [
        "实现了完整的自动写诗流程：数据加载 → 模型训练 → 逐字生成",
        "自己方案：双层 LSTM + Dropout + top-k 采样，相比指导书基线 PPL 降 14%",
        "temperature 参数对生成质量影响显著，0.8–1.0 之间效果最佳",
        "不足：val_ppl=152 仍然偏高，5 epoch 训练不够充分",
        "  改进方向①：训练 20+ epoch，PPL 有望降至 80 以下",
        "  改进方向②：用 Transformer 替换 LSTM，利用自注意力建模长程韵律",
    ])

    prs.save(str(BASE / "exp3_poetry_lstm.pptx"))
    print("exp3 done")


# ══════════════════════════════════════════════════════════
# 实验四  NMT
# ══════════════════════════════════════════════════════════
def exp4():
    prs = new_prs()

    cover(prs,
          "实验四：基于 Transformer 的神经机器翻译",
          "中英 Encoder-Decoder NMT  |  BLEU-4 = 14.93 ✅  |  PyTorch")

    content_page(prs, "概述", [
        "任务：中文→英文神经机器翻译（Chinese→English NMT）",
        "数据集：NiuTrans 开源中英平行语料库，约 100K 句对",
        "解决方案：Transformer Encoder-Decoder + 正弦位置编码",
        "  训练：teacher forcing + causal mask；推理：Beam Search",
        "评估指标：BLEU-4（目标 > 14）",
        "  最终结果：test BLEU-4 = 14.93，超过目标要求",
        "  优化路径：v1（贪心，10ep）= 12.39 → v2（beam=4，20ep）= 14.93",
    ])

    content_page(prs, "数据集介绍：NiuTrans 中英平行语料", [
        "来源：NiuTrans 项目开源数据，新闻领域中英句对",
        "规模：训练集 ~100K 对，验证集 ~1K，测试集 ~1K",
        "中文已做分词（词间空格分隔），英文转小写，不需额外分词",
        "词汇表含 3 个特殊符号：<unk>（低频词）、<s>（句首）、</s>（句尾）",
        "  中文词表约 30K，英文词表约 25K（低频词统一替换为 <unk>）",
        "数据样例：",
        "  中：北约 不少 飞机 不得不 携 返航",
        "  英：many nato planes had to return to base laden with munitions",
    ])

    content_page(prs, "解决方案：Transformer 模型结构", [
        "整体框架：Encoder-Decoder，基于 PyTorch nn.Transformer（batch_first=True）",
        "编码器（Encoder，3层）：",
        "  中文 Embedding(d=256) × √256 + 正弦位置编码",
        "  每层：多头自注意力（4头）+ FFN（d_ff=512）+ LayerNorm + 残差",
        "解码器（Decoder，3层）：",
        "  英文 Embedding × √256 + 正弦位置编码 + causal mask（防偷看未来）",
        "  每层：掩码自注意力 + 交叉注意力（与 Encoder 交互）+ FFN",
        "生成头：Linear(256 → tgt_vocab_size)，预测下一个英文词",
    ])

    two_col(prs, "解决方案：优化策略（v1→v2 改进）",
            "v1 基线（BLEU=12.39）", [
                "训练 10 epochs",
                "推理：贪心解码（argmax）",
                "无梯度裁剪",
                "验证集：100 样本 + 贪心",
                "结果不达标，差距 1.61",
            ],
            "v2 优化（BLEU=14.93 ✅）", [
                "延长训练至 20 epochs",
                "推理：Beam Search（beam=4，α=0.7）",
                "梯度裁剪（clip_norm = 1.0）",
                "Label Smoothing（ε=0.1）",
                "三项改进合计 +2.54 BLEU",
            ])

    code_page(prs, "核心代码：Beam Search 解码",
        "def beam_search_sentence(model, src_tokens, data, device,\n"
        "                          max_len, beam_size=4, length_penalty=0.7):\n"
        "    # 初始化：单条束，序列为 [<bos>]\n"
        "    beams     = [(0.0, [tgt_vocab.bos_idx])]   # (累计log概率, 序列)\n"
        "    completed = []                              # 已生成 </s> 的序列\n"
        "    for _ in range(max_len):\n"
        "        candidates = []\n"
        "        for score, seq in beams:\n"
        "            logits   = model(src, tgt_tensor, src_mask, tgt_mask)\n"
        "            log_prob = torch.log_softmax(logits[0, -1], dim=-1)\n"
        "            top_p, top_id = log_prob.topk(beam_size)\n"
        "            for p, idx in zip(top_p, top_id):\n"
        "                candidates.append((score + p, seq + [idx]))\n"
        "        # 按长度惩罚评分排序：score / len(seq)^alpha\n"
        "        candidates.sort(\n"
        "            key=lambda x: x[0] / len(x[1])**length_penalty,\n"
        "            reverse=True)\n"
        "        beams = candidates[:beam_size]",
        note="length_penalty=0.7（α<1）轻度鼓励长句，防止模型偏好过短翻译。")

    content_page(prs, "训练过程：20 epoch 收敛曲线（关键节点）", [
        "Epoch  1：dev_bleu =  4.77  （模型初步学习对齐）",
        "Epoch  4：dev_bleu = 11.96  （快速提升期，loss 从 5.9 降至 4.6）",
        "Epoch 12：dev_bleu = 14.39  （首次突破目标值 14）",
        "Epoch 13：dev_bleu = 16.63  ★ 最佳，保存 best.pt",
        "Epoch 14：dev_bleu = 16.39  （后期波动，CosineAnnealingLR 起作用）",
        "Epoch 20：dev_bleu = 15.30  （最终 epoch，损失持续缓慢下降）",
        "  使用 best.pt（epoch 13）进行测试集评估：test BLEU = 14.93",
    ])

    result_page(prs, "实验结果与分析",
        [("test BLEU-4", "14.93", "✅ > 14"),
         ("best dev BLEU", "16.63", "epoch 13"),
         ("test_loss", "3.5903", ""),
         ("v1→v2 提升", "+2.54", "")],
        [
            "翻译样例（beam=4）：",
            "  SRC：北约 不少 飞机 不得不 携 返航",
            "  HYP：many nato planes have suddenly left the us plane for the planes .",
            "  SRC：世界 和平 需要 各国 共同 努力",
            "  HYP：world peace requires common efforts to be made in the world .",
            "Beam Search 相比贪心解码提升约 +2 BLEU，长度惩罚避免了过短输出",
        ])

    content_page(prs, "总结与展望", [
        "实现了完整的 Transformer NMT：正弦位置编码、causal mask、beam search",
        "通过「延长训练 + Beam Search + 梯度裁剪」三项优化，从 12.39 提升至 14.93",
        "Label Smoothing 减少模型对训练集的过度自信，提升泛化能力",
        "当前模型层数（3层）较原论文（6层）偏浅，在 GPU 资源受限时是合理取舍",
        "  改进方向①：增大 d_model（256→512）和层数，提升模型容量",
        "  改进方向②：使用 BPE 子词分词替代词粒度，减少 OOV 问题",
        "  改进方向③：引入 Warmup 学习率调度，进一步稳定训练",
    ])

    prs.save(str(BASE / "exp4_nmt_transformer.pptx"))
    print("exp4 done")


if __name__ == "__main__":
    os.chdir(str(BASE.parent))
    exp1()
    exp2()
    exp3()
    exp4()
    print("全部完成。")
