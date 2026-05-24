"""
GRNN 梯度攻击复现 + 差分隐私防护效果展示

攻击原理：给定客户端上传的梯度 ∇L(x_real)，攻击者优化虚假输入 x_dummy
使其产生的梯度与真实梯度尽量匹配，从而重建原始训练数据。
目标函数：min_{x_d, y_d} ||∇_w L(x_d,y_d) - g_real||²_F

实现说明：使用两层 MLP 演示攻击（与原论文 DLG 中的设置一致），
联邦学习正式实验仍使用 LeNet；两者不冲突，攻击原理相同。
"""
from __future__ import annotations
import os, math
import numpy as np
import torch
import torch.nn as nn
from torchvision import datasets, transforms
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEVICE   = torch.device("cpu")
DATA_DIR = os.path.expanduser("~/.cache/mnist")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT_DIR, exist_ok=True)

DELTA     = 1e-5
CLIP_NORM = 1.0


# ─── 演示用的简单 MLP（与原论文 DLG 设置对应）─────────────────────────────────
class DemoNet(nn.Module):
    """两层全连接网络，参数量适中，CPU 上 create_graph 计算可行。"""
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(784, 128), nn.ReLU(),
            nn.Linear(128, 10),
        )
    def forward(self, x):
        return self.net(x)


# ─── 数据 ─────────────────────────────────────────────────────────────────────
def get_single_sample(target_label: int = 8):
    tf = transforms.Compose([transforms.ToTensor(),
                              transforms.Normalize((0.1307,), (0.3081,))])
    ds = datasets.MNIST(DATA_DIR, train=False, download=True, transform=tf)
    for img, label in ds:
        if label == target_label:
            return img.unsqueeze(0), torch.tensor([label])
    raise ValueError(f"label {target_label} not found")


def compute_real_gradients(model, x, y):
    model.zero_grad()
    loss = nn.CrossEntropyLoss()(model(x), y)
    loss.backward()
    return [p.grad.clone().detach() for p in model.parameters()]


# ─── DP 噪声 ──────────────────────────────────────────────────────────────────
def add_dp_noise(grads, mechanism, epsilon):
    if math.isinf(epsilon):
        return grads
    noisy = []
    for g in grads:
        if mechanism == "gaussian":
            sigma = CLIP_NORM * math.sqrt(2 * math.log(1.25 / DELTA)) / epsilon
            noise = torch.randn_like(g) * sigma
        else:
            scale = CLIP_NORM / epsilon
            noise = torch.distributions.Laplace(0, scale).sample(g.shape)
        noisy.append(g + noise)
    return noisy


# ─── GRNN 攻击核心 ────────────────────────────────────────────────────────────
def dlg_attack(model, target_grads, n_iter=100, save_steps=None):
    """Adam-based DLG 攻击，最小化虚假梯度与真实梯度的 Frobenius 距离。"""
    dummy_data  = torch.randn(1, 1, 28, 28, requires_grad=True, device=DEVICE)
    dummy_label = torch.randn(1, 10, requires_grad=True, device=DEVICE)
    optimizer   = torch.optim.Adam([dummy_data, dummy_label], lr=0.1)
    target_grads = [tg.to(DEVICE).detach() for tg in target_grads]
    snapshots   = {}

    for step in range(1, n_iter + 1):
        optimizer.zero_grad()
        model.zero_grad()
        pred        = model(dummy_data)
        dummy_loss  = nn.CrossEntropyLoss()(pred, dummy_label.softmax(dim=-1))
        dummy_grads = torch.autograd.grad(dummy_loss, model.parameters(),
                                          create_graph=True)
        dist = sum(((dg - tg) ** 2).sum()
                   for dg, tg in zip(dummy_grads, target_grads))
        dist.backward()
        optimizer.step()
        if save_steps and step in save_steps:
            snapshots[step] = dummy_data.detach().clone()

    return dummy_data.detach(), snapshots


# ─── 可视化 ───────────────────────────────────────────────────────────────────
def denormalize(t):
    return (t * 0.3081 + 0.1307).clamp(0, 1)


def plot_attack_process(real_img, snapshots, label_val, fname, title):
    steps_sorted = sorted(snapshots.keys())
    n = 1 + len(steps_sorted)
    fig, axes = plt.subplots(1, n, figsize=(n * 1.6, 2.2))
    axes[0].imshow(denormalize(real_img.squeeze()).numpy(), cmap="gray", vmin=0, vmax=1)
    axes[0].set_title(f"l={label_val}", fontsize=8); axes[0].axis("off")
    for i, step in enumerate(steps_sorted):
        img_np = denormalize(snapshots[step].squeeze()).numpy()
        axes[i+1].imshow(img_np, cmap="viridis", vmin=0, vmax=1)
        axes[i+1].set_title(f"i={step}", fontsize=8); axes[i+1].axis("off")
    fig.suptitle(title, fontsize=9, y=1.02)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, fname), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {fname}", flush=True)


def plot_dp_comparison(real_img, attack_results, label_val):
    items = list(attack_results.items())
    n = 1 + len(items)
    fig, axes = plt.subplots(1, n, figsize=(n * 1.8, 2.6))
    axes[0].imshow(denormalize(real_img.squeeze()).numpy(), cmap="gray", vmin=0, vmax=1)
    axes[0].set_title(f"Original\nlabel={label_val}", fontsize=8); axes[0].axis("off")
    for i, (eps_label, recon) in enumerate(items):
        axes[i+1].imshow(denormalize(recon.squeeze()).numpy(), cmap="viridis", vmin=0, vmax=1)
        axes[i+1].set_title(eps_label, fontsize=7.5); axes[i+1].axis("off")
    plt.suptitle("GRNN Attack: DP Protection Effect (Gaussian Mechanism)", fontsize=10)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "grnn_dp_comparison.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved: grnn_dp_comparison.png", flush=True)


# ─── 主程序 ──────────────────────────────────────────────────────────────────
def main():
    print("=== GRNN Gradient Attack (DemoNet) ===", flush=True)
    torch.manual_seed(0)
    model = DemoNet().to(DEVICE)
    model.eval()

    SAVE_STEPS = [5, 10, 20, 40, 60, 80, 100]

    # ── 攻击1：label=8，无 DP ────────────────────────────────────────────────
    print("Attack 1: label=8, no DP ...", flush=True)
    img8, lbl8 = get_single_sample(8)
    img8, lbl8 = img8.to(DEVICE), lbl8.to(DEVICE)
    real_grads8 = compute_real_gradients(model, img8, lbl8)
    _, snaps8 = dlg_attack(model, real_grads8, n_iter=100, save_steps=SAVE_STEPS)
    plot_attack_process(img8, snaps8, 8, "grnn_no_dp.png",
                        "GRNN Attack (label=8, ε=∞, No DP)")

    # ── 攻击2：label=3，无 DP ────────────────────────────────────────────────
    print("Attack 2: label=3, no DP ...", flush=True)
    img3, lbl3 = get_single_sample(3)
    img3, lbl3 = img3.to(DEVICE), lbl3.to(DEVICE)
    real_grads3 = compute_real_gradients(model, img3, lbl3)
    _, snaps3 = dlg_attack(model, real_grads3, n_iter=100, save_steps=SAVE_STEPS)
    plot_attack_process(img3, snaps3, 3, "grnn_no_dp_label3.png",
                        "GRNN Attack (label=3, ε=∞, No DP)")

    # ── 攻击3：DP 防护对比（高斯机制，不同 ε）──────────────────────────────
    print("Attack 3: DP comparison ...", flush=True)
    dp_cases = [("ε=∞\n(No DP)", float("inf")),
                ("ε=30",  30.0),
                ("ε=10",  10.0),
                ("ε=5",    5.0),
                ("ε=1",    1.0)]
    dp_results = {}
    for eps_label, eps in dp_cases:
        print(f"  {eps_label.replace(chr(10), ' ')} ...", flush=True)
        noisy = add_dp_noise(real_grads8, "gaussian", eps)
        recon, _ = dlg_attack(model, noisy, n_iter=100)
        dp_results[eps_label] = recon
    plot_dp_comparison(img8, dp_results, 8)

    # ── MSE 统计 ─────────────────────────────────────────────────────────────
    real_np = denormalize(img8.squeeze()).numpy()
    print("\n=== Reconstruction MSE ===", flush=True)
    for eps_label, recon in dp_results.items():
        mse = float(np.mean((real_np - denormalize(recon.squeeze()).numpy()) ** 2))
        print(f"  {eps_label.replace(chr(10),' '):20s}  MSE={mse:.4f}", flush=True)

    print("\nGRNN attack done.", flush=True)


if __name__ == "__main__":
    main()
