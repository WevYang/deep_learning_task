from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, write_text
from core.text import Vocab
from exp4_nmt.data import NMTData, build_nmt_dataloaders
from exp4_nmt.model import TransformerNMT
from exp4_nmt.train import translate_sentence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 4: NMT translation")
    parser.add_argument("--data_dir", type=str, default="data/nmt")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--sentence", type=str, default="北约 不少 飞机 不得不 携 返航")
    parser.add_argument("--max_length", type=int, default=80)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--save_dir", type=str, default="outputs/exp4_nmt_translate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = get_device(args.device)
    save_dir = ensure_dir(args.save_dir)
    ckpt = torch.load(args.checkpoint, map_location=device)
    data = build_nmt_dataloaders(args.data_dir, batch_size=1)
    src_vocab_dict = ckpt["src_vocab"]
    tgt_vocab_dict = ckpt["tgt_vocab"]
    src_vocab = Vocab(
        stoi=src_vocab_dict["stoi"],
        itos=src_vocab_dict["itos"],
        pad_token=src_vocab_dict["pad_token"],
        unk_token=src_vocab_dict["unk_token"],
        bos_token=src_vocab_dict["bos_token"],
        eos_token=src_vocab_dict["eos_token"],
    )
    tgt_vocab = Vocab(
        stoi=tgt_vocab_dict["stoi"],
        itos=tgt_vocab_dict["itos"],
        pad_token=tgt_vocab_dict["pad_token"],
        unk_token=tgt_vocab_dict["unk_token"],
        bos_token=tgt_vocab_dict["bos_token"],
        eos_token=tgt_vocab_dict["eos_token"],
    )
    data = NMTData(data.train_loader, data.dev_loader, data.test_loader, src_vocab, tgt_vocab)
    model = TransformerNMT(
        src_vocab_size=len(src_vocab),
        tgt_vocab_size=len(tgt_vocab),
        d_model=ckpt["args"].get("d_model", 256),
        nhead=ckpt["args"].get("nhead", 4),
        num_encoder_layers=ckpt["args"].get("num_encoder_layers", 3),
        num_decoder_layers=ckpt["args"].get("num_decoder_layers", 3),
        dim_feedforward=ckpt["args"].get("dim_feedforward", 512),
        dropout=ckpt["args"].get("dropout", 0.1),
        src_pad_idx=src_vocab.pad_idx,
        tgt_pad_idx=tgt_vocab.pad_idx,
    ).to(device)
    model.load_state_dict(ckpt["model"])
    src_tokens = args.sentence.strip().split()
    hyp_tokens = translate_sentence(model, src_tokens, data, device, args.max_length)
    output = f"source={args.sentence}\ntranslation={' '.join(hyp_tokens)}\n"
    write_text(save_dir / "translation.txt", output)
    print(output, end="")


if __name__ == "__main__":
    main()
