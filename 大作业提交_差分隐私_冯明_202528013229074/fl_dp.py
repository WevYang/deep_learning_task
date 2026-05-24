"""
联邦学习 + 差分隐私实验
- 10 个客户端，IID 划分 MNIST
- FedAvg 聚合，100 轮
- 拉普拉斯机制 / 高斯机制（多个 ε 值）
- 输出准确率曲线
"""
from __future__ import annotations
import copy, math, os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lenet import LeNet

# ─── 超参 ────────────────────────────────────────────────────────────────────
N_CLIENTS   = 10
N_ROUNDS    = 100
LOCAL_EPOCH = 1
BATCH_SIZE  = 256
LR          = 0.01
CLIP_NORM   = 1.0        # 梯度裁剪 L2 范数上界（全局灵敏度）
DELTA       = 1e-5       # 高斯机制 δ

LAPLACE_EPS  = [10.0, 25.0, 50.0, 75.0, 100.0, float("inf")]
GAUSSIAN_EPS = [1.0,  5.0,  10.0, 20.0, 30.0,  float("inf")]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATA_DIR = os.path.expanduser("~/.cache/mnist")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── 数据 ─────────────────────────────────────────────────────────────────────
def get_datasets():
    tf = transforms.Compose([transforms.ToTensor(),
                              transforms.Normalize((0.1307,), (0.3081,))])
    train = datasets.MNIST(DATA_DIR, train=True,  download=True, transform=tf)
    test  = datasets.MNIST(DATA_DIR, train=False, download=True, transform=tf)
    return train, test

def iid_split(dataset, n_clients):
    idx = torch.randperm(len(dataset)).tolist()
    size = len(dataset) // n_clients
    return [Subset(dataset, idx[i*size:(i+1)*size]) for i in range(n_clients)]

# ─── DP 噪声 ──────────────────────────────────────────────────────────────────
def clip_params(params: list[torch.Tensor], clip: float) -> list[torch.Tensor]:
    """按全局 L2 范数裁剪参数列表（模拟客户端梯度更新裁剪）。"""
    total_norm = torch.sqrt(sum(p.norm() ** 2 for p in params))
    scale = min(1.0, clip / (total_norm + 1e-8))
    return [p * scale for p in params]

def add_laplace_noise(params, clip, epsilon):
    if math.isinf(epsilon):
        return params
    scale = clip / epsilon          # Laplace 尺度参数 b = Δf / ε
    # Sample directly on same device as param (GPU-friendly)
    return [p + (torch.empty_like(p).exponential_(1/scale) -
                 torch.empty_like(p).exponential_(1/scale))
            for p in params]

def add_gaussian_noise(params, clip, epsilon, delta=DELTA):
    if math.isinf(epsilon):
        return params
    # σ = C * sqrt(2 ln(1.25/δ)) / ε  —— 高斯机制
    sigma = clip * math.sqrt(2 * math.log(1.25 / delta)) / epsilon
    return [p + torch.randn_like(p) * sigma for p in params]

# ─── 联邦学习 ─────────────────────────────────────────────────────────────────
def client_update(model, loader):
    """本地 SGD 训练，返回模型参数列表（相对于全局模型的更新量）。"""
    net = copy.deepcopy(model).to(DEVICE)
    opt = torch.optim.SGD(net.parameters(), lr=LR, momentum=0.5)
    crit = nn.CrossEntropyLoss()
    global_params = [p.data.clone() for p in net.parameters()]
    for _ in range(LOCAL_EPOCH):
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            opt.zero_grad()
            crit(net(x), y).backward()
            opt.step()
    # 返回更新量 Δw = w_local - w_global
    updates = [p.data.clone() - gp for p, gp in zip(net.parameters(), global_params)]
    return updates

def fed_avg(global_model, all_updates):
    """FedAvg：将所有客户端更新的均值加回全局模型。"""
    with torch.no_grad():
        for i, p in enumerate(global_model.parameters()):
            mean_update = torch.stack([u[i] for u in all_updates]).mean(dim=0)
            p.data += mean_update

def evaluate(model, loader):
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            correct += (model(x).argmax(1) == y).sum().item()
            total   += y.size(0)
    return correct / total

# ─── 单次实验 ─────────────────────────────────────────────────────────────────
def run_fl(train_ds, test_loader, mechanism, epsilon):
    """运行一组参数的联邦学习，返回每轮测试准确率列表。"""
    torch.manual_seed(42)
    model = LeNet().to(DEVICE)
    client_loaders = [DataLoader(s, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)
                      for s in iid_split(train_ds, N_CLIENTS)]
    acc_history = []

    for rnd in range(1, N_ROUNDS + 1):
        all_updates = []
        for loader in client_loaders:
            updates = client_update(model, loader)
            updates = clip_params(updates, CLIP_NORM)        # 裁剪
            if mechanism == "laplace":
                updates = add_laplace_noise(updates, CLIP_NORM, epsilon)
            elif mechanism == "gaussian":
                updates = add_gaussian_noise(updates, CLIP_NORM, epsilon)
            all_updates.append(updates)
        fed_avg(model, all_updates)
        if rnd % 10 == 0 or rnd == 1:
            acc = evaluate(model, test_loader)
            print(f"  Round {rnd:3d}/{N_ROUNDS}  ε={epsilon}  acc={acc:.4f}", flush=True)
        else:
            acc = None
        acc_history.append(acc)

    # 补全空缺（仅每5轮记录一次，其余插值）
    full = []
    last = 0.0
    for a in acc_history:
        if a is not None:
            last = a
        full.append(last)
    return full

# ─── 画图 ─────────────────────────────────────────────────────────────────────
COLORS = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#000000"]

def plot_curves(results: dict, mechanism: str, eps_list: list, title: str, fname: str):
    fig, ax = plt.subplots(figsize=(7, 5))
    rounds = list(range(1, N_ROUNDS + 1))
    for (eps, acc), color in zip(results.items(), COLORS):
        label = f"ε = {eps}" if not math.isinf(eps) else "ε = +∞"
        ax.plot(rounds, [a * 100 for a in acc], label=label, color=color, linewidth=1.5)
    ax.set_xlabel("Global Round", fontsize=12)
    ax.set_ylabel("Testing Accuracy (%)", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.set_xlim(0, N_ROUNDS)
    ax.set_ylim(0, 100)
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(OUT_DIR, fname)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved: {path}")

# ─── 主程序 ──────────────────────────────────────────────────────────────────
def main():
    print(f"Device: {DEVICE}  |  N_CLIENTS={N_CLIENTS}  N_ROUNDS={N_ROUNDS}")
    train_ds, test_ds = get_datasets()
    test_loader = DataLoader(test_ds, batch_size=256)

    # === 拉普拉斯机制 ===
    print("\n=== Laplace Mechanism ===")
    lap_results = {}
    for eps in LAPLACE_EPS:
        print(f"\nε = {eps}")
        lap_results[eps] = run_fl(train_ds, test_loader, "laplace", eps)
    np.save(os.path.join(OUT_DIR, "laplace_results.npy"),
            {str(k): v for k, v in lap_results.items()})
    plot_curves(lap_results, "laplace", LAPLACE_EPS,
                "Mnist Laplace Mechanism", "laplace_accuracy.png")

    # === 高斯机制 ===
    print("\n=== Gaussian Mechanism ===")
    gau_results = {}
    for eps in GAUSSIAN_EPS:
        print(f"\nε = {eps}")
        gau_results[eps] = run_fl(train_ds, test_loader, "gaussian", eps)
    np.save(os.path.join(OUT_DIR, "gaussian_results.npy"),
            {str(k): v for k, v in gau_results.items()})
    plot_curves(gau_results, "gaussian", GAUSSIAN_EPS,
                "Mnist Gaussian Mechanism", "gaussian_accuracy.png")

    # 打印最终准确率表
    print("\n=== Final Accuracy (Round 100) ===")
    print(f"{'ε':>10}  {'Laplace':>10}  {'Gaussian':>10}")
    for leps, geps in zip(LAPLACE_EPS, GAUSSIAN_EPS):
        la = lap_results[leps][-1]
        ga = gau_results[geps][-1]
        print(f"{str(leps):>10}  {la*100:>9.2f}%  {str(geps):>5} {ga*100:>8.2f}%")

if __name__ == "__main__":
    main()
