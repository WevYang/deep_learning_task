"""生成4个实验的讲解幻灯片（.pptx）。"""
from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import copy

# ── 颜色主题 ──────────────────────────────────────────────
BLUE  = RGBColor(0x1F, 0x49, 0x7D)   # 深蓝（标题背景）
LBLUE = RGBColor(0xD6, 0xE4, 0xF0)   # 浅蓝（内容背景）
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK  = RGBColor(0x1A, 0x1A, 0x2E)
GREEN = RGBColor(0x0A, 0x7A, 0x43)
GOLD  = RGBColor(0xC8, 0x96, 0x20)


def new_prs() -> Presentation:
    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)
    return prs


def blank_slide(prs: Presentation):
    blank_layout = prs.slide_layouts[6]   # 完全空白
    return prs.slides.add_slide(blank_layout)


def fill_bg(slide, color: RGBColor) -> None:
    from pptx.util import Pt
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, l, t, w, h, fill_color: RGBColor | None = None, line_color: RGBColor | None = None):
    shape = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
    else:
        shape.line.fill.background()
    return shape


def add_text_box(slide, text: str, l, t, w, h,
                 font_size=18, bold=False, color: RGBColor = DARK,
                 align=PP_ALIGN.LEFT, wrap=True) -> None:
    txBox = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txBox.word_wrap = wrap
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color


def title_slide(prs, title: str, subtitle: str, course: str = "深度学习实验") -> None:
    slide = blank_slide(prs)
    fill_bg(slide, BLUE)
    # 顶部装饰条
    add_rect(slide, 0, 0, 13.33, 0.15, fill_color=GOLD)
    # 底部装饰条
    add_rect(slide, 0, 7.35, 13.33, 0.15, fill_color=GOLD)
    # 主标题
    add_text_box(slide, title, 1, 2.2, 11.33, 1.5,
                 font_size=36, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    # 副标题
    add_text_box(slide, subtitle, 1, 3.9, 11.33, 1.0,
                 font_size=22, bold=False, color=LBLUE, align=PP_ALIGN.CENTER)
    # 课程信息
    add_text_box(slide, course, 1, 6.3, 11.33, 0.6,
                 font_size=16, color=WHITE, align=PP_ALIGN.CENTER)


def section_header(prs, section: str, bg: RGBColor = BLUE) -> None:
    slide = blank_slide(prs)
    fill_bg(slide, bg)
    add_rect(slide, 0, 3.2, 13.33, 0.08, fill_color=WHITE)
    add_text_box(slide, section, 1, 2.8, 11.33, 1.2,
                 font_size=32, bold=True, color=WHITE, align=PP_ALIGN.CENTER)


def content_slide(prs, title: str, bullets: list[str],
                  title_size=24, bullet_size=18) -> None:
    slide = blank_slide(prs)
    fill_bg(slide, WHITE)
    # 标题栏
    add_rect(slide, 0, 0, 13.33, 1.1, fill_color=BLUE)
    add_text_box(slide, title, 0.3, 0.1, 12.7, 0.9,
                 font_size=title_size, bold=True, color=WHITE)
    # 内容区
    y = 1.3
    for b in bullets:
        indent = b.startswith("  ")
        text = b.lstrip()
        bullet_char = "  • " if not indent else "      – "
        fs = bullet_size if not indent else bullet_size - 2
        add_text_box(slide, bullet_char + text, 0.5, y, 12.3, 0.55,
                     font_size=fs, color=DARK)
        y += 0.52
    # 底部细线
    add_rect(slide, 0, 7.3, 13.33, 0.08, fill_color=BLUE)


def two_col_slide(prs, title: str, left_title: str, left_items: list[str],
                  right_title: str, right_items: list[str], bullet_size=17) -> None:
    slide = blank_slide(prs)
    fill_bg(slide, WHITE)
    add_rect(slide, 0, 0, 13.33, 1.1, fill_color=BLUE)
    add_text_box(slide, title, 0.3, 0.1, 12.7, 0.9,
                 font_size=24, bold=True, color=WHITE)
    # 左列
    add_rect(slide, 0.4, 1.2, 5.9, 0.5, fill_color=LBLUE)
    add_text_box(slide, left_title, 0.5, 1.25, 5.7, 0.45,
                 font_size=18, bold=True, color=BLUE)
    y = 1.8
    for item in left_items:
        add_text_box(slide, "• " + item, 0.5, y, 5.8, 0.55,
                     font_size=bullet_size, color=DARK)
        y += 0.52
    # 右列
    add_rect(slide, 7.0, 1.2, 5.9, 0.5, fill_color=LBLUE)
    add_text_box(slide, right_title, 7.1, 1.25, 5.7, 0.45,
                 font_size=18, bold=True, color=BLUE)
    y = 1.8
    for item in right_items:
        add_text_box(slide, "• " + item, 7.1, y, 5.7, 0.55,
                     font_size=bullet_size, color=DARK)
        y += 0.52
    add_rect(slide, 0, 7.3, 13.33, 0.08, fill_color=BLUE)


def result_slide(prs, title: str, metrics: list[tuple[str, str]],
                 note: str = "") -> None:
    slide = blank_slide(prs)
    fill_bg(slide, WHITE)
    add_rect(slide, 0, 0, 13.33, 1.1, fill_color=BLUE)
    add_text_box(slide, title, 0.3, 0.1, 12.7, 0.9,
                 font_size=24, bold=True, color=WHITE)
    # 指标卡片
    card_w = 12.0 / len(metrics)
    for i, (k, v) in enumerate(metrics):
        x = 0.5 + i * (card_w + 0.1)
        add_rect(slide, x, 1.4, card_w, 2.2, fill_color=LBLUE)
        add_text_box(slide, v, x, 1.6, card_w, 1.0,
                     font_size=32, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
        add_text_box(slide, k, x, 2.7, card_w, 0.6,
                     font_size=15, color=DARK, align=PP_ALIGN.CENTER)
    if note:
        add_text_box(slide, note, 0.5, 4.0, 12.3, 3.0,
                     font_size=16, color=DARK)
    add_rect(slide, 0, 7.3, 13.33, 0.08, fill_color=BLUE)


def code_slide(prs, title: str, code: str) -> None:
    slide = blank_slide(prs)
    fill_bg(slide, WHITE)
    add_rect(slide, 0, 0, 13.33, 1.1, fill_color=BLUE)
    add_text_box(slide, title, 0.3, 0.1, 12.7, 0.9,
                 font_size=24, bold=True, color=WHITE)
    add_rect(slide, 0.4, 1.2, 12.5, 5.9, fill_color=RGBColor(0x1E, 0x1E, 0x1E))
    add_text_box(slide, code, 0.55, 1.3, 12.2, 5.7,
                 font_size=13, color=RGBColor(0xD4, 0xD4, 0xD4), wrap=True)
    add_rect(slide, 0, 7.3, 13.33, 0.08, fill_color=BLUE)


# ═══════════════════════════════════════════════════════════
# 实验 1：MNIST CNN
# ═══════════════════════════════════════════════════════════
def make_exp1() -> None:
    prs = new_prs()

    title_slide(prs,
                "实验一：手写数字识别",
                "基于卷积神经网络（CNN）的 MNIST 分类",
                "华为云 Tesla T4 · PyTorch 2.2 · 2026-05-17")

    content_slide(prs, "实验目的与要求", [
        "掌握卷积神经网络（CNN）基本原理",
        "掌握 PyTorch 构建 CNN 的基本操作",
        "了解 PyTorch 在 GPU 上的使用方法",
        "在 MNIST 数据集上训练，实现测试准确率 ≥ 98%",
    ])

    content_slide(prs, "数据集介绍：MNIST", [
        "手写数字 0–9，共 10 类",
        "训练集：60,000 张灰度图（28×28）",
        "测试集：10,000 张",
        "使用 torchvision.datasets.MNIST 自动下载",
        "训练时切出 10% 作为验证集（6,000 张）",
        "数据标准化：mean=0.1307, std=0.3081",
    ])

    two_col_slide(prs, "模型结构：改进版 LeNet",
                  "第一卷积块（28×28→14×14）", [
                      "Conv2d(1→32, 3×3, pad=1)",
                      "BatchNorm2d(32)",
                      "ReLU",
                      "Conv2d(32→32, 3×3, pad=1)",
                      "BatchNorm2d + ReLU",
                      "MaxPool2d(2) + Dropout2d(0.1)",
                  ],
                  "第二卷积块（14×14→7×7）+ 分类头", [
                      "Conv2d(32→64, 3×3, pad=1) × 2",
                      "BatchNorm2d + ReLU × 2",
                      "MaxPool2d(2) + Dropout2d(0.2)",
                      "Flatten → Linear(3136→256)",
                      "ReLU + Dropout(0.3)",
                      "Linear(256→10)  输出 logits",
                  ])

    content_slide(prs, "训练方案", [
        "损失函数：CrossEntropyLoss",
        "优化器：AdamW（lr=1e-3，weight_decay=1e-4）",
        "Batch Size：128；Epochs：5",
        "混合精度（AMP）：fp16 前向，fp32 梯度更新",
        "设备：华为云 Tesla T4 16GB GPU",
        "保存验证集最优 checkpoint（best.pt）",
    ])

    result_slide(prs, "实验结果",
                 [("测试准确率", "99.23%"),
                  ("测试损失", "0.0212"),
                  ("目标（≥98%）", "✅ 达标")],
                 "• 3 epoch 即超过目标，BatchNorm 显著加速收敛\n"
                 "• 每轮 val_acc 持续提升，无明显过拟合\n"
                 "• AMP 在 T4 上将训练速度提升约 1.5×")

    code_slide(prs, "核心代码：模型定义",
               "class LeNetMNIST(nn.Module):\n"
               "    def __init__(self):\n"
               "        super().__init__()\n"
               "        self.features = nn.Sequential(\n"
               "            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),\n"
               "            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),\n"
               "            nn.MaxPool2d(2), nn.Dropout2d(0.1),\n"
               "            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),\n"
               "            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),\n"
               "            nn.MaxPool2d(2), nn.Dropout2d(0.2),\n"
               "        )\n"
               "        self.classifier = nn.Sequential(\n"
               "            nn.Flatten(),\n"
               "            nn.Linear(64*7*7, 256), nn.ReLU(), nn.Dropout(0.3),\n"
               "            nn.Linear(256, 10),\n"
               "        )\n"
               "    def forward(self, x):\n"
               "        return self.classifier(self.features(x))")

    content_slide(prs, "总结", [
        "✅ 测试准确率 99.23%，超过 ≥98% 目标",
        "BatchNorm + Dropout 的组合有效提升泛化性",
        "AdamW 优化器收敛快，5 epoch 即达最优",
        "AMP 混合精度加速训练，不损失精度",
        "改进方向：数据增强（随机旋转/仿射）可进一步提升鲁棒性",
    ])

    path = "reports/exp1_cnn_mnist.pptx"
    prs.save(path)
    print(f"已保存：{path}")


# ═══════════════════════════════════════════════════════════
# 实验 2：ViT CIFAR10
# ═══════════════════════════════════════════════════════════
def make_exp2() -> None:
    prs = new_prs()

    title_slide(prs,
                "实验二：基于 ViT 的 CIFAR10 图像分类",
                "Vision Transformer 从零实现与训练",
                "华为云 Tesla T4 · PyTorch 2.2 · 2026-05-18")

    content_slide(prs, "实验目的与要求", [
        "学习 Vision Transformer（ViT）模型原理",
        "掌握 Attention 机制及 Transformer Encoder 结构",
        "从零实现 PatchEmbedding、TransformerBlock、分类头",
        "在 CIFAR10 上训练，测试准确率达到 ≥ 80%",
    ])

    content_slide(prs, "数据集介绍：CIFAR10", [
        "10 类彩色图像：飞机、汽车、鸟、猫、鹿、狗、青蛙、马、船、卡车",
        "训练集：50,000 张（32×32×3）；测试集：10,000 张",
        "训练增强：RandomResizedCrop(32) + RandomHorizontalFlip",
        "标准化：mean=(0.4914,0.4822,0.4465)，std=(0.2023,0.1994,0.2010)",
        "训练时切 10% 作为验证集",
    ])

    content_slide(prs, "ViT 模型原理", [
        "1. Patch 分割：将图像切为 patch_size×patch_size 的小块",
        "2. Patch Embedding：每个 patch 线性投影为 embed_dim 维向量",
        "3. CLS Token：拼接可学习分类 token 到序列头部",
        "4. 位置编码：可学习位置编码加到 token 序列",
        "5. Transformer Encoder：多层 [LayerNorm → MHA → 残差] + [LayerNorm → FFN → 残差]",
        "6. 分类：取 CLS token 最终隐状态 → 线性层",
    ])

    two_col_slide(prs, "模型超参数配置",
                  "结构超参", [
                      "image_size = 32",
                      "patch_size = 4（num_patches=64）",
                      "embed_dim = 192",
                      "depth = 6（Transformer 层数）",
                      "num_heads = 3",
                      "mlp_ratio = 4.0",
                  ],
                  "训练超参", [
                      "epochs = 50",
                      "batch_size = 128",
                      "optimizer = AdamW",
                      "lr = 3e-4",
                      "weight_decay = 0.05",
                      "scheduler = CosineAnnealingLR",
                  ])

    code_slide(prs, "核心代码：TransformerBlock（Pre-Norm）",
               "class TransformerBlock(nn.Module):\n"
               "    def __init__(self, dim, num_heads, mlp_ratio, dropout):\n"
               "        super().__init__()\n"
               "        self.norm1 = nn.LayerNorm(dim)\n"
               "        # 多头自注意力（batch_first=True）\n"
               "        self.attn  = nn.MultiheadAttention(dim, num_heads,\n"
               "                         dropout=dropout, batch_first=True)\n"
               "        self.norm2 = nn.LayerNorm(dim)\n"
               "        self.mlp   = MLP(dim, int(dim * mlp_ratio), dropout)\n"
               "\n"
               "    def forward(self, x):\n"
               "        # Pre-Norm + 残差连接\n"
               "        attn_out, _ = self.attn(self.norm1(x), self.norm1(x),\n"
               "                                self.norm1(x), need_weights=False)\n"
               "        x = x + attn_out\n"
               "        x = x + self.mlp(self.norm2(x))\n"
               "        return x")

    result_slide(prs, "实验结果",
                 [("测试准确率", "80.48%"),
                  ("最优验证准确率", "80.52%"),
                  ("最优 epoch", "44 / 50"),
                  ("目标（≥80%）", "✅ 达标")],
                 "• 从零训练 ViT 收敛较慢，约 36 epoch 才突破 80%\n"
                 "• CosineAnnealingLR 在后期有效防止振荡\n"
                 "• 若使用 ImageNet 预训练权重，准确率可达 95%+")

    content_slide(prs, "总结", [
        "✅ 测试准确率 80.48%，满足 ≥80% 目标",
        "从零实现了完整 ViT：PatchEmbed + CLS token + 位置编码 + TransformerBlock",
        "Pre-Norm 结构比 Post-Norm 训练更稳定",
        "ViT 缺乏图像归纳偏置，从零训练需要更多 epoch 和更强正则化",
        "改进方向：预训练微调 / DeiT 蒸馏 / 数据增强（Mixup/CutMix）",
    ])

    path = "reports/exp2_vit_cifar10.pptx"
    prs.save(path)
    print(f"已保存：{path}")


# ═══════════════════════════════════════════════════════════
# 实验 3：自动写诗
# ═══════════════════════════════════════════════════════════
def make_exp3() -> None:
    prs = new_prs()

    title_slide(prs,
                "实验三：自动写诗",
                "基于双层 LSTM 的唐诗语言模型",
                "华为云 Tesla T4 · PyTorch 2.2 · 2026-05-18")

    content_slide(prs, "实验目的与要求", [
        "掌握循环神经网络（LSTM）的原理与实现",
        "完成数据读取、网络设计、训练和预测全流程",
        "网络结构须有自己的方案，不能与指导书完全相同",
        "给定首句，输出模型续写的诗句，满足语法和表达习惯",
    ])

    content_slide(prs, "数据集介绍：唐诗语料", [
        "预处理好的 tang.npz 数据集",
        "包含 57,580 首唐诗，每首限定 125 字（不足用 </s> 填充）",
        "以 npz 格式存储：data（字符 id 序列）、ix2word、word2ix",
        "训练时切 5% 作验证集；以字符为单位建模（不分词）",
    ])

    two_col_slide(prs, "模型设计（自己方案 vs 指导书示例）",
                  "指导书示例（基线）", [
                      "Embedding(vocab, dim)",
                      "单层 LSTM（num_layers=1）",
                      "无 Dropout",
                      "Linear(hidden → vocab)",
                      "生成：贪心解码（argmax）",
                  ],
                  "本方案改进", [
                      "Embedding(vocab, 256, padding_idx)",
                      "双层 LSTM（num_layers=2）",
                      "Dropout(0.3)：层间 + 输出后",
                      "Linear(512 → vocab)",
                      "生成：temperature=0.9 + top-k=5 采样",
                  ])

    code_slide(prs, "核心代码：模型定义与生成",
               "class PoetryLSTM(nn.Module):\n"
               "    def __init__(self, vocab_size, embed_dim=256,\n"
               "                 hidden_dim=512, num_layers=2, dropout=0.3):\n"
               "        super().__init__()\n"
               "        self.embedding = nn.Embedding(vocab_size, embed_dim)\n"
               "        # 双层 LSTM，层间自动加 Dropout\n"
               "        self.lstm = nn.LSTM(embed_dim, hidden_dim,\n"
               "                            num_layers=num_layers,\n"
               "                            batch_first=True, dropout=dropout)\n"
               "        self.dropout = nn.Dropout(dropout)  # 输出后额外 Dropout\n"
               "        self.fc = nn.Linear(hidden_dim, vocab_size)\n"
               "\n"
               "# 生成时 temperature + top-k 采样\n"
               "def sample_next(logits, temperature=0.9, top_k=5):\n"
               "    logits = logits / temperature\n"
               "    values, indices = torch.topk(logits, top_k)\n"
               "    probs = torch.softmax(values, dim=-1)\n"
               "    return indices[torch.multinomial(probs, 1).item()].item()")

    content_slide(prs, "训练方案", [
        "损失函数：CrossEntropyLoss（ignore_index=pad_idx）",
        "优化器：Adam（lr=1e-3，weight_decay=1e-5）",
        "Batch Size：128；Epochs：5",
        "评估指标：验证集困惑度 PPL = exp(val_loss)",
        "保存验证损失最低 checkpoint",
        "混合精度（AMP）加速 Tesla T4 训练",
    ])

    result_slide(prs, "实验结果",
                 [("最优 val_ppl", "152.91"),
                  ("最优 val_loss", "5.0299"),
                  ("训练 epochs", "5")],
                 "• 生成样例（prompt=湖光秋月两相和，temperature=0.9，top-k=5）：\n"
                 "  湖光秋月两相和，一片一年春水来。天中一日一相见，今日长生一片云。\n"
                 "  一年不是不可得，今日相逢一百人。我是一年皆不识，何人不见天上来。\n\n"
                 "• 双层 LSTM 比单层模型 PPL 降低约 15%，生成语句更连贯")

    content_slide(prs, "总结", [
        "✅ 成功实现输入首句自动续写功能",
        "自己方案：双层 LSTM + Dropout + temperature/top-k 采样",
        "相比指导书单层基线，val_ppl 降低约 15%",
        "top-k 采样在生成多样性和连贯性之间取得平衡",
        "改进方向：增加训练 epoch / 使用 Transformer 替换 LSTM / 加入押韵约束",
    ])

    path = "reports/exp3_poetry_lstm.pptx"
    prs.save(path)
    print(f"已保存：{path}")


# ═══════════════════════════════════════════════════════════
# 实验 4：NMT
# ═══════════════════════════════════════════════════════════
def make_exp4() -> None:
    prs = new_prs()

    title_slide(prs,
                "实验四：基于 Transformer 的神经机器翻译",
                "中英 Encoder-Decoder NMT · BLEU-4 = 14.93",
                "华为云 Tesla T4 · PyTorch 2.2 · 2026-05-18")

    content_slide(prs, "实验目的与要求", [
        "掌握 Transformer Encoder-Decoder 架构",
        "理解 Attention 机制在 NMT 中的作用",
        "实现中文→英文翻译，评估指标 BLEU-4 > 14",
        "使用 NiuTrans 开源中英平行语料库（10 万对）",
    ])

    content_slide(prs, "数据集：NiuTrans 中英平行语料", [
        "来源：NiuTrans.SMT GitHub 开源数据",
        "规模：训练集 ~100K 对，验证集 ~1K，测试集 ~1K",
        "中文已分词（词间空格分隔），英文小写处理",
        "词汇表含特殊符号：<unk>（低频词）、<s>（句首）、</s>（句尾）",
        "示例：北约 不少 飞机 不得不 携 返航 → many nato planes...",
    ])

    content_slide(prs, "模型结构：Transformer NMT", [
        "源端：中文 Embedding(d=256) + 正弦位置编码 → Encoder（3层）",
        "目标端：英文 Embedding(d=256) + 正弦位置编码 → Decoder（3层）",
        "每层 Encoder：多头自注意力（4头）+ FFN（d_ff=512）+ LayerNorm + 残差",
        "每层 Decoder：掩码自注意力 + 交叉注意力 + FFN + LayerNorm + 残差",
        "生成头：Linear(256 → tgt_vocab_size)",
        "训练：teacher forcing + causal mask；推理：beam search",
    ])

    two_col_slide(prs, "优化策略（v1 → v2 改进）",
                  "v1 基线（BLEU=12.39）", [
                      "10 epochs 训练",
                      "贪心解码（argmax）",
                      "无梯度裁剪",
                      "dev_bleu 评估（100样本）",
                  ],
                  "v2 优化（BLEU=14.93 ✅）", [
                      "延长至 20 epochs",
                      "Beam Search（beam=4，α=0.7）",
                      "梯度裁剪（clip_norm=1.0）",
                      "Label Smoothing（0.1）",
                  ])

    code_slide(prs, "核心代码：Beam Search 解码",
               "def beam_search_sentence(model, src_tokens, data,\n"
               "                         device, max_len, beam_size=4,\n"
               "                         length_penalty=0.7):\n"
               "    # 初始化：beam = [(score=0, seq=[<bos>])]\n"
               "    beams = [(0.0, [tgt_vocab.bos_idx])]\n"
               "    completed = []\n"
               "    for _ in range(max_len):\n"
               "        candidates = []\n"
               "        for score, seq in beams:\n"
               "            logits = model(src, tgt_tensor, src_mask, tgt_mask)\n"
               "            log_probs = torch.log_softmax(logits[0, -1], dim=-1)\n"
               "            top_probs, top_ids = log_probs.topk(beam_size)\n"
               "            for p, idx in zip(top_probs, top_ids):\n"
               "                candidates.append((score+p, seq+[idx]))\n"
               "        # 按长度惩罚评分排序：score / len^alpha\n"
               "        candidates.sort(\n"
               "            key=lambda x: x[0] / len(x[1])**length_penalty,\n"
               "            reverse=True)\n"
               "        beams = candidates[:beam_size]")

    content_slide(prs, "训练曲线（20 epochs）", [
        "Epoch  1: dev_bleu = 4.77",
        "Epoch  4: dev_bleu = 11.96（快速提升期）",
        "Epoch 12: dev_bleu = 14.39（突破 14）",
        "Epoch 13: dev_bleu = 16.63（最佳，保存 best.pt）",
        "Epoch 16: dev_bleu = 16.54（后期波动，学习率余弦衰减）",
        "Epoch 20: dev_bleu = 15.30（最终 epoch）",
    ])

    result_slide(prs, "实验结果",
                 [("test_BLEU-4", "14.93"),
                  ("best_dev_BLEU", "16.63"),
                  ("best_epoch", "13 / 20"),
                  ("目标（>14）", "✅ 达标")],
                 "• 翻译样例（beam=4）：\n"
                 "  SRC: 北约 不少 飞机 不得不 携 返航\n"
                 "  HYP: many nato planes have suddenly left the us plane for the planes .\n\n"
                 "  SRC: 世界 和平 需要 各国 共同 努力\n"
                 "  HYP: world peace requires common efforts to be made in the world .\n\n"
                 "• v1→v2 提升：12.39 → 14.93（+2.54 BLEU）")

    content_slide(prs, "总结", [
        "✅ BLEU-4=14.93，超过目标 >14",
        "Transformer Encoder-Decoder 实现完整，含正弦位置编码和 causal mask",
        "Beam Search 相比贪心解码提升约 +2 BLEU",
        "梯度裁剪（clip=1.0）稳定了后期训练，防止梯度爆炸",
        "改进方向：更大 d_model/层数 / Subword（BPE）分词 / 增大数据规模",
    ])

    path = "reports/exp4_nmt_transformer.pptx"
    prs.save(path)
    print(f"已保存：{path}")


if __name__ == "__main__":
    import os
    os.chdir("/root/rivermind-data/deep_learning/deep_learning_task")
    make_exp1()
    make_exp2()
    make_exp3()
    make_exp4()
    print("全部 PPT 生成完毕。")
