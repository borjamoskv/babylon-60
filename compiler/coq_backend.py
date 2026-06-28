#!/usr/bin/env python3
# C5-REAL: Coq Translation Backend for BABYLON-60 Proof IR

import sys
import os

def parse_ir(file_path):
    with open(file_path, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines

def translate_to_coq(ir_lines):
    coq_code = [
        "(* Auto-generated Coq Backend for BABYLON-60 *)",
        "Require Import Coq.Init.Nat.",
        "Require Import Coq.Strings.String.",
        "",
        "Module Babylon60.",
        "",
        "(* Core state declarations *)",
        "Definition Reg : Type := nat.",
        "Definition Val : Type := string.",
        "Definition EventId : Type := string.",
        "",
        "(* Axiomatic Trace Declarations *)",
    ]

    for line in ir_lines:
        line = line.strip("()")
        parts = line.split()
        if not parts:
            continue
        
        tag = parts[0]
        if tag == "Event":
            ev_id = parts[1]
            tick = parts[2]
            coq_code.append(f"Parameter ev_tick_{ev_id} : nat.")
            coq_code.append(f"Axiom ev_tick_{ev_id}_val : ev_tick_{ev_id} = {tick}.")
        elif tag == "HappensBefore":
            coq_code.append(f"Axiom causal_{parts[1]}_{parts[2]} : ev_tick_{parts[1]} <= ev_tick_{parts[2]}.")
        elif tag == "Assign":
            event_id = parts[-1]
            reg = parts[1]
            val = " ".join(parts[2:-1])
            coq_code.append(f"Parameter assign_{event_id} : Val.")
            coq_code.append(f"Axiom assign_{event_id}_val : assign_{event_id} = \"{val}\"%string.")
        elif tag == "Add":
            event_id = parts[-1]
            reg = parts[1]
            val = " ".join(parts[2:-1])
            coq_code.append(f"Parameter add_{event_id} : Val.")
            coq_code.append(f"Axiom add_{event_id}_val : add_{event_id} = \"{val}\"%string.")
        elif tag == "Sub":
            event_id = parts[-1]
            reg = parts[1]
            val = " ".join(parts[2:-1])
            coq_code.append(f"Parameter sub_{event_id} : Val.")
            coq_code.append(f"Axiom sub_{event_id}_val : sub_{event_id} = \"{val}\"%string.")
        elif tag == "Spawn":
            event_id = parts[-1]
            target = " ".join(parts[1:-1])
            coq_code.append(f"Parameter spawn_{event_id} : string.")
            coq_code.append(f"Axiom spawn_{event_id}_val : spawn_{event_id} = \"{target}\"%string.")
        elif tag == "Block":
            event_id = parts[-1]
            symbol = " ".join(parts[1:-1])
            coq_code.append(f"Parameter await_{event_id} : string.")
            coq_code.append(f"Axiom await_{event_id}_val : await_{event_id} = \"{symbol}\"%string.")
        elif tag == "Wait":
            event_id = parts[-1]
            ticks = parts[1]
            coq_code.append(f"Parameter after_{event_id} : nat.")
            coq_code.append(f"Axiom after_{event_id}_val : after_{event_id} = {ticks}.")
        elif tag == "Emit":
            event_id = parts[-1]
            action = " ".join(parts[1:-1])
            coq_code.append(f"Parameter emit_{event_id} : string.")
            coq_code.append(f"Axiom emit_{event_id}_val : emit_{event_id} = \"{action}\"%string.")

    coq_code.append("")
    coq_code.append("End Babylon60.")
    coq_code.append("")
    
    return "\n".join(coq_code)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 coq_backend.py <path_to_proof.ir>")
        sys.exit(1)
        
    ir_file = sys.argv[1]
    if not os.path.exists(ir_file):
        print(f"Error: {ir_file} not found.")
        sys.exit(1)
        
    ir_lines = parse_ir(ir_file)
    coq_code = translate_to_coq(ir_lines)
    
    out_file = "BabylonTrace.v"
    with open(out_file, "w") as f:
        f.write(coq_code)
        
    print(f"[Coq Backend] Generated {out_file} successfully.")

if __name__ == "__main__":
    main()
