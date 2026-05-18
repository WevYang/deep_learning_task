from __future__ import annotations

import argparse
import sys

import torch

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, write_text
from core.text import Vocab
from exp7_lm.model import LSTMLanguageModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 7: PTB language generation")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--prompt", type=str, default="the")
    parser.add_argument("--max_len", type=int, default=50)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top_k", type=int, default=20)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save_dir", type=str, default="outputs/exp7_lm_generate")
    return parser.parse_args()


def sample_next(logits: torch.Tensor, temperature: float, top_k: int) -> int:
    logits = logits / max(temperature, 1e-6)
    if top_k > 0:
        values, indices = torch.topk(logits, min(top_k, logits.size(-1)))
        probs = torch.softmax(values, dim=-1)
        sampled = torch.multinomial(probs, 1).item()
        return int(indices[sampled].item())
    probs = torch.softmax(logits, dim=-1)
    return int(torch.multinomial(probs, 1).item())


def generate(
    model: LSTMLanguageModel,
    vocab: Vocab,
    prompt: str,
    max_len: int,
    temperature: float,
    top_k: int,
    device: torch.device,
) -> str:
    model.eval()
    tokens = ["<bos>"] + [t.lower() for t in prompt.strip().split() if t.strip()]
    input_ids = [vocab.stoi.get(tok, vocab.unk_idx) for tok in tokens]
    hidden = None
    last_logits = None
    with torch.no_grad():
        for idx in input_ids:
            logits, hidden = model(torch.tensor([[idx]], device=device), hidden)
            last_logits = logits[0, -1]
        generated = prompt.strip().split()
        for _ in range(max_len):
            if last_logits is None:
                break
            next_id = sample_next(last_logits, temperature, top_k)
            token = vocab.itos[next_id]
            if token == "<eos>":
                break
            generated.append(token)
            cur = torch.tensor([[next_id]], device=device)
            logits, hidden = model(cur, hidden)
            last_logits = logits[0, -1]
    return " ".join(generated)


def main() -> None:
    args = parse_args()
    device = get_device(args.device)
    save_dir = ensure_dir(args.save_dir)
    ckpt = torch.load(args.checkpoint, map_location=device)
    vocab_dict = ckpt["vocab"]
    vocab = Vocab(
        stoi=vocab_dict["stoi"],
        itos=vocab_dict["itos"],
        pad_token=vocab_dict["pad_token"],
        unk_token=vocab_dict["unk_token"],
        bos_token=vocab_dict["bos_token"],
        eos_token=vocab_dict["eos_token"],
    )
    model = LSTMLanguageModel(
        vocab_size=len(vocab),
        emb_size=ckpt["args"].get("emb_size", 650),
        hidden_size=ckpt["args"].get("hidden_size", 650),
        num_layers=ckpt["args"].get("num_layers", 2),
        dropout=ckpt["args"].get("dropout", 0.5),
        tie_weights=True,
        pad_idx=vocab.pad_idx,
    ).to(device)
    model.load_state_dict(ckpt["model"])
    text = generate(
        model,
        vocab,
        args.prompt,
        args.max_len,
        args.temperature,
        args.top_k,
        device,
    )
    output = f"prompt={args.prompt}\ntext={text}\n"
    write_text(save_dir / "generated.txt", output)
    print(output, end="")


if __name__ == "__main__":
    main()
