from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, timestamp, write_text
from core.metrics import compute_bleu
from exp4_nmt.data import NMTData, build_nmt_dataloaders
from exp4_nmt.model import TransformerNMT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 4: Transformer NMT training")
    parser.add_argument("--data_dir", type=str, default="data/nmt")
    parser.add_argument("--save_dir", type=str, default="outputs/exp4_nmt")
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--d_model", type=int, default=256)
    parser.add_argument("--nhead", type=int, default=4)
    parser.add_argument("--num_encoder_layers", type=int, default=3)
    parser.add_argument("--num_decoder_layers", type=int, default=3)
    parser.add_argument("--dim_feedforward", type=int, default=512)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--max_length", type=int, default=80)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--max_train_samples", type=int, default=None)
    parser.add_argument("--max_dev_samples", type=int, default=None)
    parser.add_argument("--max_test_samples", type=int, default=None)
    parser.add_argument("--beam_size", type=int, default=4)      # 测试时的 beam 宽度
    parser.add_argument("--beam_alpha", type=float, default=0.7)  # 长度惩罚指数 α
    parser.add_argument("--grad_clip", type=float, default=1.0)   # 梯度裁剪阈值，防止梯度爆炸
    return parser.parse_args()


@torch.no_grad()
def evaluate_loss(model: nn.Module, loader: torch.utils.data.DataLoader, device: torch.device, criterion: nn.Module) -> float:
    """计算验证/测试集上的平均 token 级交叉熵损失（忽略 padding token）。"""
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    for src, tgt_in, tgt_out, src_padding_mask, tgt_padding_mask in loader:
        src = src.to(device)
        tgt_in = tgt_in.to(device)
        tgt_out = tgt_out.to(device)
        src_padding_mask = src_padding_mask.to(device)
        tgt_padding_mask = tgt_padding_mask.to(device)
        logits = model(src, tgt_in, src_padding_mask, tgt_padding_mask)
        loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_out.reshape(-1))
        valid = tgt_out.ne(criterion.ignore_index).sum().item()
        total_loss += loss.item() * max(valid, 1)
        total_tokens += max(valid, 1)
    return total_loss / total_tokens


def train_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    criterion: nn.Module,
    scaler: torch.cuda.amp.GradScaler | None,
    grad_clip: float = 1.0,
) -> float:
    model.train()
    total_loss = 0.0
    total_tokens = 0
    for src, tgt_in, tgt_out, src_padding_mask, tgt_padding_mask in tqdm(loader, desc="train", leave=False):
        src = src.to(device)
        tgt_in = tgt_in.to(device)
        tgt_out = tgt_out.to(device)
        src_padding_mask = src_padding_mask.to(device)
        tgt_padding_mask = tgt_padding_mask.to(device)
        optimizer.zero_grad(set_to_none=True)
        if scaler is not None:
            with torch.cuda.amp.autocast():
                logits = model(src, tgt_in, src_padding_mask, tgt_padding_mask)
                loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_out.reshape(-1))
            scaler.scale(loss).backward()
            if grad_clip > 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            scaler.step(optimizer)
            scaler.update()
        else:
            logits = model(src, tgt_in, src_padding_mask, tgt_padding_mask)
            loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_out.reshape(-1))
            loss.backward()
            if grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
        valid = tgt_out.ne(criterion.ignore_index).sum().item()
        total_loss += loss.item() * max(valid, 1)
        total_tokens += max(valid, 1)
    return total_loss / total_tokens


@torch.no_grad()
def beam_search_sentence(
    model: TransformerNMT,
    src_tokens: list[str],
    data: NMTData,
    device: torch.device,
    max_len: int,
    beam_size: int = 4,
    length_penalty: float = 0.7,
) -> list[str]:
    """Beam Search 解码单句。

    维护 beam_size 条候选序列，按 score / len^alpha 做长度惩罚排序，
    避免模型偏好短句。alpha=0.7 为常用经验值。
    """
    src_vocab = data.src_vocab
    tgt_vocab = data.tgt_vocab
    src_ids = [src_vocab.bos_idx] + src_vocab.encode(src_tokens) + [src_vocab.eos_idx]
    src_tensor = torch.tensor([src_ids], dtype=torch.long, device=device)
    src_mask = src_tensor.eq(src_vocab.pad_idx)

    beams: list[tuple[float, list[int]]] = [(0.0, [tgt_vocab.bos_idx])]
    completed: list[tuple[float, list[int]]] = []

    for _ in range(max_len):
        if not beams:
            break
        candidates: list[tuple[float, list[int]]] = []
        for score, seq in beams:
            if seq[-1] == tgt_vocab.eos_idx:
                completed.append((score, seq))
                continue
            tgt_tensor = torch.tensor([seq], dtype=torch.long, device=device)
            tgt_mask = tgt_tensor.eq(tgt_vocab.pad_idx)
            logits = model(src_tensor, tgt_tensor, src_mask, tgt_mask)
            log_probs = torch.log_softmax(logits[0, -1], dim=-1)
            top_probs, top_ids = log_probs.topk(beam_size)
            for p, idx in zip(top_probs.tolist(), top_ids.tolist()):
                candidates.append((score + p, seq + [idx]))
        if not candidates:
            break
        candidates.sort(key=lambda x: x[0] / (len(x[1]) ** length_penalty), reverse=True)
        beams = []
        for score, seq in candidates[:beam_size]:
            if seq[-1] == tgt_vocab.eos_idx:
                completed.append((score, seq))
            else:
                beams.append((score, seq))
        if len(completed) >= beam_size:
            break

    completed.extend(beams)
    if not completed:
        return []
    best = max(completed, key=lambda x: x[0] / (max(len(x[1]), 1) ** length_penalty))
    result = tgt_vocab.decode(best[1][1:])
    return [t for t in result if t not in {"</s>", "<pad>"}]


@torch.no_grad()
def translate_sentence(
    model: TransformerNMT,
    src_tokens: list[str],
    data: NMTData,
    device: torch.device,
    max_len: int,
) -> list[str]:
    src_vocab = data.src_vocab
    tgt_vocab = data.tgt_vocab
    src_ids = [src_vocab.bos_idx] + src_vocab.encode(src_tokens) + [src_vocab.eos_idx]
    src_tensor = torch.tensor([src_ids], dtype=torch.long, device=device)
    src_mask = src_tensor.eq(src_vocab.pad_idx)
    generated = [tgt_vocab.bos_idx]
    for _ in range(max_len):
        tgt_tensor = torch.tensor([generated], dtype=torch.long, device=device)
        tgt_mask = tgt_tensor.eq(tgt_vocab.pad_idx)
        logits = model(src_tensor, tgt_tensor, src_mask, tgt_mask)
        next_id = int(logits[0, -1].argmax(dim=-1).item())
        generated.append(next_id)
        if next_id == tgt_vocab.eos_idx:
            break
    return tgt_vocab.decode(generated[1:])


@torch.no_grad()
def evaluate_bleu(
    model: TransformerNMT,
    loader: torch.utils.data.DataLoader,
    data: NMTData,
    device: torch.device,
    max_len: int,
    beam_size: int = 1,
    beam_alpha: float = 0.7,
) -> float:
    model.eval()
    references: list[list[list[str]]] = []
    hypotheses: list[list[str]] = []
    for src, tgt_in, tgt_out, src_padding_mask, tgt_padding_mask in loader:
        src = src.to(device)
        batch_refs = []
        for row in tgt_out:
            tokens = data.tgt_vocab.decode(row.tolist())
            tokens = [tok for tok in tokens if tok not in {"<pad>", "<s>"}]
            if "</s>" in tokens:
                tokens = tokens[: tokens.index("</s>")]
            batch_refs.append([tokens])
        batch_hyps = []
        for row in src:
            tokens = data.src_vocab.decode(row.tolist())
            tokens = [tok for tok in tokens if tok not in {"<pad>", "<s>", "</s>"}]
            if beam_size > 1:
                batch_hyps.append(beam_search_sentence(model, tokens, data, device, max_len, beam_size, beam_alpha))
            else:
                batch_hyps.append(translate_sentence(model, tokens, data, device, max_len))
        references.extend(batch_refs)
        hypotheses.extend(batch_hyps)
    return compute_bleu(references, hypotheses)


def plot_history(history: list[dict[str, float]], save_dir: Path) -> None:
    epochs = [item["epoch"] for item in history]
    train_loss = [item["train_loss"] for item in history]
    dev_loss = [item["dev_loss"] for item in history]
    dev_bleu = [item["dev_bleu"] for item in history]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(epochs, train_loss, label="train_loss")
    ax1.plot(epochs, dev_loss, label="dev_loss")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("loss")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(epochs, dev_bleu, "--", label="dev_bleu")
    ax2.set_ylabel("BLEU")
    ax2.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(save_dir / "training_curve.png", dpi=160)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)
    save_dir = ensure_dir(args.save_dir)
    run_dir = ensure_dir(save_dir / timestamp())

    data = build_nmt_dataloaders(
        args.data_dir,
        batch_size=args.batch_size,
        max_length=args.max_length,
        num_workers=args.num_workers,
        max_train_samples=args.max_train_samples,
        max_dev_samples=args.max_dev_samples,
        max_test_samples=args.max_test_samples,
    )

    model = TransformerNMT(
        src_vocab_size=len(data.src_vocab),
        tgt_vocab_size=len(data.tgt_vocab),
        d_model=args.d_model,
        nhead=args.nhead,
        num_encoder_layers=args.num_encoder_layers,
        num_decoder_layers=args.num_decoder_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        src_pad_idx=data.src_vocab.pad_idx,
        tgt_pad_idx=data.tgt_vocab.pad_idx,
    ).to(device)
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs)
    # label_smoothing=0.1：标签平滑，减少模型对正确答案的过度自信，提升 BLEU
    criterion = nn.CrossEntropyLoss(ignore_index=data.tgt_vocab.pad_idx, label_smoothing=0.1)
    scaler = torch.cuda.amp.GradScaler() if (args.amp and device.type == "cuda") else None

    history: list[dict[str, float]] = []
    best_dev_bleu = 0.0
    best_path = run_dir / "best.pt"
    log_lines = [f"device={device}", f"epochs={args.epochs}", f"batch_size={args.batch_size}"]

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, data.train_loader, optimizer, device, criterion, scaler, args.grad_clip)
        dev_loss = evaluate_loss(model, data.dev_loader, device, criterion)
        dev_bleu = evaluate_bleu(model, data.dev_loader, data, device, args.max_length)
        scheduler.step()
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": train_loss,
                "dev_loss": dev_loss,
                "dev_bleu": dev_bleu,
            }
        )
        log_lines.append(
            f"epoch={epoch} train_loss={train_loss:.4f} dev_loss={dev_loss:.4f} dev_bleu={dev_bleu:.4f}"
        )
        if dev_bleu >= best_dev_bleu:
            best_dev_bleu = dev_bleu
            torch.save(
                {
                    "model": model.state_dict(),
                    "src_vocab": {
                        "stoi": data.src_vocab.stoi,
                        "itos": data.src_vocab.itos,
                        "pad_token": data.src_vocab.pad_token,
                        "unk_token": data.src_vocab.unk_token,
                        "bos_token": data.src_vocab.bos_token,
                        "eos_token": data.src_vocab.eos_token,
                    },
                    "tgt_vocab": {
                        "stoi": data.tgt_vocab.stoi,
                        "itos": data.tgt_vocab.itos,
                        "pad_token": data.tgt_vocab.pad_token,
                        "unk_token": data.tgt_vocab.unk_token,
                        "bos_token": data.tgt_vocab.bos_token,
                        "eos_token": data.tgt_vocab.eos_token,
                    },
                    "args": vars(args),
                    "epoch": epoch,
                },
                best_path,
            )

    test_loss = evaluate_loss(model, data.test_loader, device, criterion)
    # Load best checkpoint for final beam search evaluation
    ckpt = torch.load(best_path, map_location=device)
    model.load_state_dict(ckpt["model"])
    test_bleu = evaluate_bleu(model, data.test_loader, data, device, args.max_length,
                               beam_size=args.beam_size, beam_alpha=args.beam_alpha)
    torch.save({"model": model.state_dict(), "src_vocab": data.src_vocab.__dict__, "tgt_vocab": data.tgt_vocab.__dict__, "args": vars(args)}, run_dir / "last.pt")
    save_json(
        {"history": history, "best_dev_bleu": best_dev_bleu, "test_loss": test_loss, "test_bleu": test_bleu},
        run_dir / "metrics.json",
    )
    write_text(run_dir / "train.log", "\n".join(log_lines + [f"test_loss={test_loss:.4f} test_bleu={test_bleu:.4f}"]))
    plot_history(history, run_dir)

    samples = []
    for src, tgt_in, tgt_out, src_padding_mask, tgt_padding_mask in data.test_loader:
        for row in range(min(3, src.size(0))):
            src_tokens = data.src_vocab.decode(src[row].tolist())
            src_tokens = [tok for tok in src_tokens if tok not in {"<pad>", "<s>", "</s>"}]
            hyp_tokens = translate_sentence(model, src_tokens, data, device, args.max_length)
            ref_tokens = data.tgt_vocab.decode(tgt_out[row].tolist())
            ref_tokens = [tok for tok in ref_tokens if tok not in {"<pad>", "<s>", "</s>"}]
            samples.append(
                f"SRC: {' '.join(src_tokens)}\nREF: {' '.join(ref_tokens)}\nHYP: {' '.join(hyp_tokens)}\n"
            )
        break
    write_text(run_dir / "samples.txt", "\n".join(samples))

    print(f"best_dev_bleu={best_dev_bleu:.4f}")
    print(f"test_bleu={test_bleu:.4f}")
    print(f"artifacts={run_dir}")


if __name__ == "__main__":
    main()
