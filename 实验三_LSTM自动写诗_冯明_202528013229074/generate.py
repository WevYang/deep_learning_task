from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, set_seed, write_text
from exp3_poetry.model import PoetryLSTM


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 3: Poetry generation")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--start", type=str, default="湖光秋月两相和")
    parser.add_argument("--max_len", type=int, default=80)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save_dir", type=str, default="outputs/exp3_poetry_generate")
    return parser.parse_args()


def sample_next(logits: torch.Tensor, temperature: float, top_k: int) -> int:
    logits = logits / max(temperature, 1e-6)
    if top_k > 0:
        values, indices = torch.topk(logits, min(top_k, logits.size(-1)))
        probs = torch.softmax(values, dim=-1)
        next_idx = torch.multinomial(probs, 1).item()
        return int(indices[next_idx].item())
    probs = torch.softmax(logits, dim=-1)
    return int(torch.multinomial(probs, 1).item())


def generate(
    model: PoetryLSTM,
    start: str,
    ix2word: dict[int, str],
    word2ix: dict[str, int],
    device: torch.device,
    max_len: int,
    temperature: float,
    top_k: int,
) -> str:
    model.eval()
    tokens = ["<START>"] + list(start)
    input_ids = torch.tensor([[word2ix.get(tok, word2ix["</s>"]) for tok in tokens]], device=device)
    hidden = None
    last_logits = None
    with torch.no_grad():
        for idx in input_ids[0]:
            logits, hidden = model(idx.view(1, 1), hidden)
            last_logits = logits[0, -1]
        results = list(start)
        for _ in range(max_len):
            if last_logits is None:
                break
            next_id = sample_next(last_logits, temperature=temperature, top_k=top_k)
            next_token = ix2word[next_id]
            if next_token == "<EOP>" or next_token == "</s>":
                break
            results.append(next_token)
            logits, hidden = model(torch.tensor([[next_id]], device=device), hidden)
            last_logits = logits[0, -1]
    return "".join(results)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)
    save_dir = ensure_dir(args.save_dir)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model = PoetryLSTM(
        vocab_size=len(ckpt["word2ix"]),
        embed_dim=ckpt["args"].get("embed_dim", 256),
        hidden_dim=ckpt["args"].get("hidden_dim", 512),
        num_layers=ckpt["args"].get("num_layers", 2),
        dropout=ckpt["args"].get("dropout", 0.3),
        pad_idx=ckpt["word2ix"]["</s>"],
    ).to(device)
    model.load_state_dict(ckpt["model"])
    poem = generate(
        model,
        start=args.start,
        ix2word=ckpt["ix2word"],
        word2ix=ckpt["word2ix"],
        device=device,
        max_len=args.max_len,
        temperature=args.temperature,
        top_k=args.top_k,
    )
    output = f"prompt={args.start}\npoem={poem}\n"
    write_text(save_dir / "generated.txt", output)
    print(output, end="")


if __name__ == "__main__":
    main()
