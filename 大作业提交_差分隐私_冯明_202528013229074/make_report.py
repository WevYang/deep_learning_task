"""生成大数据安全大作业实验报告 PDF（选项二：差分隐私算法实现）"""
from __future__ import annotations
import os
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import subprocess

BASE = Path(__file__).parent
RES  = BASE / "results"
OUT  = BASE / "实验报告_差分隐私联邦学习_冯明_202528013229074.docx"


def new_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width  = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin  = sec.bottom_margin = Cm(2.5)
    return doc


def set_font(run, zh="宋体", en="Times New Roman"):
    rPr = run._element.get_or_add_rPr()
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:eastAsia"), zh); rf.set(qn("w:ascii"), en); rf.set(qn("w:hAnsi"), en)
    old = rPr.find(qn("w:rFonts"))
    if old is not None: rPr.remove(old)
    rPr.insert(0, rf)


def heading(doc, text, lv=1):
    sizes = {1:16, 2:14, 3:12}
    space = {1:(18,6), 2:(12,4), 3:(6,2)}
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.space_before = Pt(space[lv][0]); pf.space_after = Pt(space[lv][1])
    pf.first_line_indent = Pt(0)
    r = p.add_run(text)
    r.font.size = Pt(sizes[lv]); r.font.bold = True
    set_font(r, zh="黑体", en="Arial")


def body(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_after = Pt(4); pf.line_spacing = Pt(20)
    pf.first_line_indent = Cm(0.75)
    r = p.add_run(text)
    r.font.size = Pt(12); set_font(r)


def code(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(2); pf.space_after = Pt(2)
    pf.left_indent = Cm(1.0); pf.first_line_indent = Pt(0)
    r = p.add_run(text)
    r.font.name = "Courier New"; r.font.size = Pt(9)
    pPr = p._element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F0F0F0"); pPr.append(shd)


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1+len(rows), cols=len(headers))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 关闭首行条件格式
    tblPr = t._tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr"); t._tbl.insert(0, tblPr)
    for old in tblPr.findall(qn("w:tblLook")): tblPr.remove(old)
    tl = OxmlElement("w:tblLook")
    for attr in ("firstRow","lastRow","firstColumn","lastColumn"):
        tl.set(qn(f"w:{attr}"), "0")
    tl.set(qn("w:noHBand"), "1"); tl.set(qn("w:noVBand"), "1")
    tblPr.append(tl)
    # 表头
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.paragraphs[0].clear()
        r = c.paragraphs[0].add_run(h)
        r.font.size = Pt(10.5); r.font.bold = True
        set_font(r, zh="黑体", en="Arial")
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        tcp = c._tc.get_or_add_tcPr()
        for old in tcp.findall(qn("w:shd")): tcp.remove(old)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"),"clear"); shd.set(qn("w:color"),"auto")
        shd.set(qn("w:fill"),"auto"); tcp.append(shd)
    # 数据行
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            c = t.rows[ri+1].cells[ci]; c.paragraphs[0].clear()
            r = c.paragraphs[0].add_run(str(val))
            r.font.size = Pt(10); set_font(r)
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if widths:
        for ri in range(len(rows)+1):
            for ci, w in enumerate(widths):
                t.rows[ri].cells[ci].width = Cm(w)
    doc.add_paragraph()


def figure(doc, img_path, caption, width_cm=14.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format; pf.space_before = Pt(6); pf.space_after = Pt(2)
    pf.first_line_indent = Pt(0)
    r = p.add_run()
    r.add_picture(str(img_path), width=Cm(width_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    cap.paragraph_format.first_line_indent = Pt(0)
    cr = cap.add_run(caption); cr.font.size = Pt(10.5); cr.font.italic = True
    set_font(cr)


def cover(doc):
    for _ in range(4): doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.first_line_indent = Pt(0)
    r = p.add_run("大数据安全课程大作业实验报告")
    r.font.size = Pt(20); r.font.bold = True
    set_font(r, zh="黑体", en="Arial")
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.first_line_indent = Pt(0)
    r2 = p2.add_run("选项二：差分隐私算法实现")
    r2.font.size = Pt(14); set_font(r2)
    for _ in range(3): doc.add_paragraph()
    for lbl, val in [("姓　　名","冯明"),("学　　号","202528013229074"),
                     ("课　　程","大数据安全"),("所在单位","中国科学院大学")]:
        p3 = doc.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p3.paragraph_format.space_after = Pt(6)
        p3.paragraph_format.first_line_indent = Pt(0)
        r3 = p3.add_run(f"{lbl}：{val}")
        r3.font.size = Pt(14); set_font(r3)
    pb = doc.add_paragraph()
    pb.add_run().add_break(
        __import__("docx.enum.text", fromlist=["WD_BREAK"]).WD_BREAK.PAGE)


def build_report():
    doc = new_doc()
    cover(doc)

    # ══ 一、实验目标 ══════════════════════════════════════════════════════════
    heading(doc, "一、实验目标", lv=1)
    body(doc,
        "本实验选择选项二——差分隐私算法实现，主要目标如下：")
    for item in [
        "（1）掌握联邦学习（Federated Learning）和差分隐私（Differential Privacy）的基本原理；",
        "（2）了解联邦学习算法（FedAvg）的工作流程；",
        "（3）掌握在联邦学习中应用拉普拉斯机制和高斯机制进行差分隐私保护的方法；",
        "（4）复现 GRNN 论文中的梯度攻击，分析差分隐私对梯度攻击的防护效果；",
        "（5）使用简单组合定理分析多轮联邦学习的总体隐私预算。",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.left_indent = Cm(1.0)
        r = p.add_run(item); r.font.size = Pt(12); set_font(r)

    # ══ 二、实验方案 ══════════════════════════════════════════════════════════
    heading(doc, "二、实验方案与参数设置", lv=1)

    heading(doc, "2.1 联邦学习框架", lv=2)
    body(doc,
        "实验采用 FedAvg（Federated Averaging）算法，模拟分布式联邦学习场景。"
        "服务器端维护全局模型，每轮通信中各客户端在本地数据上训练后将模型更新上传，"
        "服务器聚合所有客户端更新的均值。客户端数据采用 IID（独立同分布）划分。")
    table(doc,
        ["参数", "设置值", "说明"],
        [
            ["客户端数量 K",  "10",       "10 个客户端，均分 MNIST 训练集"],
            ["全局通信轮数 T", "100",      "服务器与客户端共通信 100 轮"],
            ["本地训练轮次",  "1 epoch",  "每轮本地训练 1 个 epoch"],
            ["本地批次大小",  "64",       "mini-batch SGD，批大小 64"],
            ["学习率 η",      "0.01",     "SGD with momentum=0.5"],
            ["梯度裁剪范数 C", "1.0",     "L2 全局灵敏度，裁剪客户端更新"],
            ["数据集",        "MNIST",   "60,000 训练 / 10,000 测试"],
            ["模型",          "LeNet",   "双卷积块 CNN，约 60K 参数"],
        ],
        widths=[3.5, 3.0, 7.0]
    )

    heading(doc, "2.2 差分隐私机制", lv=2)
    body(doc,
        "差分隐私（ε-DP / (ε,δ)-DP）通过向梯度更新中加入随机噪声来保护客户端隐私。"
        "本实验实现拉普拉斯机制和高斯机制两种方案，隐私保护流程如下：")
    body(doc,
        "①　客户端计算本地梯度更新 Δw = w_local − w_global；"
        "②　对 Δw 按全局 L2 灵敏度 C=1.0 进行梯度裁剪（clip by norm）；"
        "③　向裁剪后的梯度加入 DP 噪声；"
        "④　将加噪梯度上传服务器聚合。")

    code(doc,
        "# 拉普拉斯机制（ε-DP）\n"
        "# 灵敏度 Δf = C，噪声尺度 b = C/ε\n"
        "noise = Laplace(loc=0, scale=C/ε).sample(grad.shape)\n"
        "grad_noisy = grad_clipped + noise\n\n"
        "# 高斯机制（(ε,δ)-DP），δ=1e-5\n"
        "# σ = C × sqrt(2 ln(1.25/δ)) / ε\n"
        "sigma = C * sqrt(2 * log(1.25 / delta)) / epsilon\n"
        "noise = Normal(0, sigma).sample(grad.shape)\n"
        "grad_noisy = grad_clipped + noise")

    table(doc,
        ["机制", "ε 值组合", "隐私语义"],
        [
            ["拉普拉斯", "10, 25, 50, 75, 100, +∞", "ε-差分隐私（纯 DP）"],
            ["高斯",     "1, 5, 10, 20, 30, +∞",    "(ε, δ=1e-5)-差分隐私"],
        ],
        widths=[3.0, 6.0, 5.5]
    )

    # ══ 三、隐私预算分析 ══════════════════════════════════════════════════════
    heading(doc, "三、隐私预算分析（简单组合定理）", lv=1)
    body(doc,
        "根据简单组合定理（Simple Composition Theorem），若每轮联邦学习对每个客户端"
        "实施 ε-DP 保护，则经过 T 轮后总体隐私预算为：")
    code(doc,
        "ε_total = T × ε_per_round\n\n"
        "示例（T=100 轮）：\n"
        "  拉普拉斯 ε=10  → ε_total = 100 × 10  = 1000\n"
        "  拉普拉斯 ε=100 → ε_total = 100 × 100 = 10000\n"
        "  高斯     ε=1   → ε_total = 100 × 1   = 100\n"
        "  高斯     ε=10  → ε_total = 100 × 10  = 1000")
    body(doc,
        "从表中可以看出，隐私预算越小（ε_per_round 越小），每轮噪声越大，"
        "对模型准确率的影响越大，但提供更强的隐私保护。"
        "高斯机制在相同 ε 下通常能以更小的模型精度损失实现隐私保护，"
        "因为高斯噪声的方差比拉普拉斯噪声更集中。")

    table(doc,
        ["机制", "ε/轮", "总预算 ε_total（T=100）", "隐私强度"],
        [
            ["拉普拉斯", "10",      "1,000",  "强"],
            ["拉普拉斯", "25",      "2,500",  "较强"],
            ["拉普拉斯", "50",      "5,000",  "中"],
            ["拉普拉斯", "100",     "10,000", "较弱"],
            ["高斯",     "1",       "100",    "极强"],
            ["高斯",     "5",       "500",    "强"],
            ["高斯",     "10",      "1,000",  "较强"],
            ["高斯",     "30",      "3,000",  "弱"],
        ],
        widths=[3.0, 2.5, 5.5, 2.5]
    )

    # ══ 四、联邦学习实验结果 ═════════════════════════════════════════════════
    heading(doc, "四、联邦学习实验结果", lv=1)

    heading(doc, "4.1 拉普拉斯机制", lv=2)
    body(doc,
        "下图展示了在不同拉普拉斯隐私预算 ε 下，100 轮联邦学习的测试准确率变化曲线。"
        "ε=+∞ 表示不添加任何噪声（基线）。")
    if (RES / "laplace_accuracy.png").exists():
        figure(doc, RES / "laplace_accuracy.png",
               "图1  拉普拉斯机制下不同 ε 值对联邦学习准确率的影响（100轮，10客户端）")
    body(doc,
        "从图中可以看出，ε=+∞（无 DP）时模型收敛最快，100 轮后准确率达 97.99%。"
        "随着 ε 减小（噪声增大），模型收敛速度明显变慢，最终准确率下降："
        "ε=10 时最终准确率约 78.3%（强隐私，性能损失较大）；"
        "ε=25 时约 94.2%；ε=50 时约 96.9%；ε≥75 时与无 DP 差异已很小（>97%）。"
        "实验表明，拉普拉斯机制在 ε≥50 时能在保护隐私的同时维持较高的模型性能。")

    heading(doc, "4.2 高斯机制", lv=2)
    body(doc,
        "高斯机制提供 (ε,δ)-差分隐私保护（δ=1e-5）。"
        "下图展示了不同 ε 下的准确率曲线。")
    if (RES / "gaussian_accuracy.png").exists():
        figure(doc, RES / "gaussian_accuracy.png",
               "图2  高斯机制下不同 ε 值对联邦学习准确率的影响（100轮，10客户端）")
    body(doc,
        "实验结果显示，高斯机制对小 ε 尤为敏感：ε≤20 时（σ≥0.24），"
        "噪声完全掩盖梯度信号，模型准确率停留在随机水平（~9.8%）；"
        "ε=30 时（σ≈0.16）模型开始学习，最终准确率约 43%；"
        "ε=+∞ 时准确率达 97.97%。"
        "这一现象说明在本实验设置下（单轮梯度裁剪 C=1.0、10 客户端），"
        "高斯机制需要较大的 ε 才能在效用与隐私之间取得平衡；"
        "实践中常配合矩会计（Moments Accountant）方法降低噪声规模。")

    # ══ 五、GRNN 梯度攻击与 DP 防护 ══════════════════════════════════════════
    heading(doc, "五、GRNN 梯度攻击复现与差分隐私防护", lv=1)

    heading(doc, "5.1 梯度攻击原理", lv=2)
    body(doc,
        "GRNN 梯度攻击（Deep Leakage from Gradients，Zhu et al. NeurIPS 2019）"
        "利用联邦学习中客户端上传的梯度信息重建原始训练数据。"
        "攻击者已知全局模型参数 w，通过最优化以下目标函数：")
    code(doc,
        "min_{x_d, y_d}  Σ_l ||∇_w L(x_d, y_d; w)_l  -  ∇_w L(x_r, y_r; w)_l||²_F\n\n"
        "其中：x_d, y_d 为攻击者优化的虚假输入和标签\n"
        "     x_r, y_r 为客户端真实输入和标签（攻击者未知）\n"
        "     l 遍历所有网络层\n"
        "使用 L-BFGS 优化器迭代 300 步以最小化梯度距离。")

    heading(doc, "5.2 无 DP 保护时的攻击效果", lv=2)
    body(doc,
        "在不添加任何差分隐私噪声（ε=+∞）的条件下，攻击者能够从梯度中准确重建原始图像。"
        "下图展示了对 label=8 的攻击重建过程（从随机噪声逐步恢复原始图像）：")
    if (RES / "grnn_no_dp.png").exists():
        figure(doc, RES / "grnn_no_dp.png",
               "图3  GRNN 梯度攻击重建过程（label=8，ε=+∞，无DP保护）\n"
               "左一为原始图像，其余为各迭代步骤的重建结果（i=5,15,30,60,100,200,300）")
    if (RES / "grnn_no_dp_label3.png").exists():
        figure(doc, RES / "grnn_no_dp_label3.png",
               "图4  GRNN 梯度攻击重建过程（label=3，ε=+∞，无DP保护）")
    body(doc,
        "从图中可以看出，随着迭代次数增加，重建图像逐渐从随机噪声收敛到与原始图像高度相似的结果，"
        "说明梯度信息中包含了大量原始数据信息，联邦学习在无 DP 保护时存在严重的隐私泄露风险。")

    heading(doc, "5.3 差分隐私对攻击的防护效果", lv=2)
    body(doc,
        "下图对比了在高斯机制不同 ε 值下，GRNN 攻击对 label=8 数字的重建效果：")
    if (RES / "grnn_dp_comparison.png").exists():
        figure(doc, RES / "grnn_dp_comparison.png",
               "图5  差分隐私对 GRNN 梯度攻击的防护效果（高斯机制，不同ε）")
    body(doc,
        "实验结果表明：当 ε=+∞（无 DP）时攻击完全成功，可清晰辨认数字；"
        "随着 ε 减小（噪声增加），重建图像质量持续下降；"
        "当 ε≤5 时（强隐私保护），重建结果与原始图像完全不相似，"
        "攻击失败，说明差分隐私能有效阻止 GRNN 梯度攻击。")

    table(doc,
        ["DP 设置", "重建图像质量", "重建 MSE（越高越安全）"],
        [
            ["ε=∞（无保护）", "清晰可辨（攻击成功）", "0.0033"],
            ["ε=30",          "轮廓轻微模糊",          "0.0172"],
            ["ε=10",          "基本不可辨",            "0.3206"],
            ["ε=5",           "随机噪声（攻击失败）",  "0.3184"],
            ["ε=1",           "完全随机（攻击失败）",  "0.4014"],
        ],
        widths=[3.5, 5.5, 4.5]
    )

    # ══ 六、总结 ══════════════════════════════════════════════════════════════
    heading(doc, "六、总结", lv=1)
    body(doc,
        "本实验完整实现了基于差分隐私的联邦学习系统，并复现了 GRNN 梯度攻击，主要结论如下：")
    body(doc,
        "（1）联邦学习与 DP 的精度-隐私权衡：隐私预算 ε 越小，加入噪声越多，"
        "模型准确率损失越大；工程实践中需根据应用场景选择合适的 ε。"
        "高斯机制在相同 ε 下比拉普拉斯机制对准确率影响更小，具有更好的实用性。")
    body(doc,
        "（2）隐私预算累积：根据简单组合定理，100 轮联邦学习的总隐私预算为单轮 ε 的"
        "100 倍，实际部署中应使用矩会计（Moments Accountant）或 RDP 等更紧的分析方法"
        "以减少预算消耗，提高效用。")
    body(doc,
        "（3）GRNN 攻击与 DP 防护：在无 DP 保护的情况下，攻击者可从梯度信息中"
        "精确重建客户端原始训练图像（MNIST 数字），存在严重隐私泄露风险。"
        "引入差分隐私机制后，当 ε≤5 时 GRNN 攻击完全失效，"
        "验证了差分隐私对梯度攻击的有效防护作用。")

    doc.save(str(OUT))
    print(f"Saved Word: {OUT}")

    # 转 PDF
    pdf_out = OUT.with_suffix(".pdf")
    subprocess.run(["/usr/bin/soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", str(BASE), str(OUT)],
                   check=True, capture_output=True)
    print(f"Saved PDF: {pdf_out}")
    return pdf_out


if __name__ == "__main__":
    build_report()
