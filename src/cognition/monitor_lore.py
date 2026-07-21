#!/usr/bin/env python3
"""
monitor_stop.py

Usage:
  1) Run your training in tmux / separate terminal and redirect stdout to a log file:
       python3 train_packy_lora.py 2>&1 | tee train.log

  2) In another terminal (tmux/ssh), run:
       python3 monitor_stop.py --log train.log --pid <TRAIN_PID>

  Or let the script find the PID by process name:
       python3 monitor_stop.py --log train.log --procname train_packy_lora.py

This script reads the log file, extracts last reported 'loss' and 'grad_norm'
(works with lines like "'loss': 1.3534, 'grad_norm': 9.71806, ..."), and decides when to stop.

Behavior/rules:
 - Checkpoints considered every time a new loss/grad_norm line appears.
 - If relative loss improvement averaged over the last N_CHECKPOINTS (default 3)
   is < REL_IMP_THRESH (default 0.005 -> 0.5%), we signal stop.
 - If grad_norm > GRAD_NORM_ABORT (default 20) -> abort immediately.
 - If grad_norm increases by >= GRAD_RISE_FACTOR (default 1.5) over last N_CHECKPOINTS -> abort.
 - Hard cap: if iter >= HARD_ITER_CAP (default 200), stop.
"""

import re
import time
import argparse
import os
import signal
from collections import deque

LOSS_REGEX = re.compile(r"'loss'\s*:\s*([0-9]*\.?[0-9]+)")
GRAD_REGEX = re.compile(r"'grad_norm'\s*:\s*([0-9]*\.?[0-9]+)")
ITER_REGEX = re.compile(r"\|\s*(\d+)\/\s*\d+\b")  # extract " 110/500" style


def tail_file(path, start_pos=0):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(start_pos)
        while True:
            line = f.readline()
            if not line:
                time.sleep(1.0)
                continue
            yield line


def find_pid_by_name(name):
    # simple ps scan; returns first PID matching name
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as c:
                cmd = c.read().decode(errors="ignore").replace("\x00", " ")
                if name in cmd:
                    return int(pid)
        except Exception:
            continue
    return None


def parse_metrics(line):
    loss_m = LOSS_REGEX.search(line)
    grad_m = GRAD_REGEX.search(line)
    iter_m = ITER_REGEX.search(line)
    loss = float(loss_m.group(1)) if loss_m else None
    grad = float(grad_m.group(1)) if grad_m else None
    itr = int(iter_m.group(1)) if iter_m else None
    return loss, grad, itr


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True, help="training log file (tee stdout to this)")
    p.add_argument("--pid", type=int, help="PID of training process to signal")
    p.add_argument("--procname", type=str, help="optional process name to auto-find PID")
    p.add_argument(
        "--checkpoints", type=int, default=3, help="how many checkpoints to average (default 3)"
    )
    p.add_argument(
        "--rel_imp_thresh",
        type=float,
        default=0.005,
        help="relative loss improvement threshold to stop (default 0.005 = 0.5%)",
    )
    p.add_argument(
        "--grad_norm_abort",
        type=float,
        default=20.0,
        help="absolute grad_norm abort threshold (default 20)",
    )
    p.add_argument(
        "--grad_rise_factor",
        type=float,
        default=1.5,
        help="if grad_norm increases by this factor over last N, abort (default 1.5)",
    )
    p.add_argument(
        "--hard_iter_cap", type=int, default=200, help="hard iteration cap fallback (default 200)"
    )
    args = p.parse_args()

    pid = args.pid
    if not pid and args.procname:
        pid = find_pid_by_name(args.procname)
        if pid:
            print(f"[monitor] Found process {args.procname} -> PID {pid}")
    if not pid:
        print(
            "[monitor] No PID provided. You can still run monitor to watch logs and it will only print alerts (won't send signals)."
        )
    else:
        print(f"[monitor] Will signal PID {pid} (SIGINT) when stop conditions met.")

    # tail file from end
    startpos = os.path.getsize(args.log) if os.path.exists(args.log) else 0
    reader = tail_file(args.log, start_pos=startpos)

    losses = deque(maxlen=args.checkpoints + 1)
    grads = deque(maxlen=args.checkpoints + 1)
    iters = deque(maxlen=args.checkpoints + 1)

    print("[monitor] Watching log:", args.log)
    for line in reader:
        loss, grad, itr = parse_metrics(line)
        if loss is None and grad is None and itr is None:
            continue

        if loss is not None:
            losses.append(loss)
        if grad is not None:
            grads.append(grad)
        if itr is not None:
            iters.append(itr)

        # only evaluate when we have enough checkpoints (>= check_count)
        if len(losses) >= args.checkpoints:
            # compute relative improvement over last window
            # use oldest and newest in the deque
            old_loss = losses[0]
            new_loss = losses[-1]
            rel_imp = (old_loss - new_loss) / max(1e-12, old_loss)
            avg_grad = sum(grads) / len(grads) if grads else None

            print(
                f"[monitor] it={iters[-1] if iters else 'N/A'} loss={new_loss:.4f} rel_imp(last_window)={rel_imp:.4%} avg_grad={avg_grad:.3f}"
            )

            # abort conditions
            abort = False
            reason = None

            # 1) grad_norm absolute threshold
            if avg_grad is not None and avg_grad > args.grad_norm_abort:
                abort = True
                reason = f"avg_grad {avg_grad:.2f} > grad_abort {args.grad_norm_abort}"

            # 2) grad_norm rising trend: compare newest grad to oldest
            if not abort and len(grads) >= args.checkpoints:
                if grads[0] > 0:
                    rise_factor = grads[-1] / max(1e-12, grads[0])
                    if rise_factor >= args.grad_rise_factor:
                        abort = True
                        reason = (
                            f"grad_norm rose by factor {rise_factor:.2f} >= {args.grad_rise_factor}"
                        )

            # 3) loss plateau: relative improvement below threshold
            if not abort and rel_imp < args.rel_imp_thresh:
                abort = True
                reason = (
                    f"loss relative improvement {rel_imp:.4%} < threshold {args.rel_imp_thresh:.2%}"
                )

            # 4) hard iteration cap
            if not abort and iters and iters[-1] >= args.hard_iter_cap:
                abort = True
                reason = f"hard iter cap reached ({iters[-1]} >= {args.hard_iter_cap})"

            if abort:
                msg = f"[monitor] STOP condition met at iter {iters[-1] if iters else 'N/A'}: {reason}"
                print(msg)
                if pid:
                    try:
                        os.kill(pid, signal.SIGINT)
                        print(f"[monitor] Sent SIGINT to PID {pid}")
                    except Exception as e:
                        print(f"[monitor] Failed to signal PID {pid}: {e}")
                else:
                    print(
                        "[monitor] No PID supplied - not signaling. Run with --pid or --procname to enable signaling."
                    )
                break


if __name__ == "__main__":
    main()
