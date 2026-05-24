"""从保存的 .npy 文件重新生成准确率曲线，图例改为总体隐私预算 ε_total = T×ε"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import math, os

RES = os.path.join(os.path.dirname(__file__), "results")
N_ROUNDS = 100
COLORS = ["#d62728","#ff7f0e","#2ca02c","#1f77b4","#9467bd","#000000"]

def plot(npy_file, eps_list, title, fname, total_eps_list):
    data = np.load(os.path.join(RES, npy_file), allow_pickle=True).item()
    rounds = list(range(1, N_ROUNDS + 1))
    fig, ax = plt.subplots(figsize=(8, 5))
    for eps, total_eps, color in zip(eps_list, total_eps_list, COLORS):
        acc = data[str(eps)]
        if math.isinf(eps):
            label = r"$\varepsilon_{total}$ = +∞（无噪声基线）"
        else:
            label = r"$\varepsilon_{total}$" + f" = {int(total_eps)}"
        ax.plot(rounds, [a * 100 for a in acc], label=label,
                color=color, linewidth=1.8)
    ax.set_xlabel("Global Round", fontsize=12)
    ax.set_ylabel("Testing Accuracy (%)", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.set_xlim(1, N_ROUNDS); ax.set_ylim(0, 100)
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RES, fname)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")

LAP_EPS   = [10.0, 25.0, 50.0, 75.0, 100.0, float("inf")]
LAP_TOTAL = [1000, 2500, 5000, 7500, 10000, float("inf")]
plot("laplace_results.npy", LAP_EPS,
     "Laplace Mechanism: Effect of Total Privacy Budget on FL Accuracy\n"
     "(T=100 rounds, K=10 clients, MNIST+LeNet)",
     "laplace_accuracy.png", LAP_TOTAL)

GAU_EPS   = [1.0, 5.0, 10.0, 20.0, 30.0, float("inf")]
GAU_TOTAL = [100, 500, 1000, 2000, 3000, float("inf")]
plot("gaussian_results.npy", GAU_EPS,
     "Gaussian Mechanism: Effect of Total Privacy Budget on FL Accuracy\n"
     "(T=100 rounds, K=10 clients, MNIST+LeNet, delta=1e-5)",
     "gaussian_accuracy.png", GAU_TOTAL)

print("Done.")
