(* Auto-generated Coq Backend for BABYLON-60 *)
Require Import Coq.Init.Nat.
Require Import Coq.Strings.String.

Module Babylon60.

(* Core state declarations *)
Definition Reg : Type := nat.
Definition Val : Type := string.
Definition EventId : Type := string.

(* Axiomatic Trace Declarations *)
Parameter ev_tick_EV_2 : nat.
Axiom ev_tick_EV_2_val : ev_tick_EV_2 = 2.
Parameter assign_EV_2 : Val.
Axiom assign_EV_2_val : assign_EV_2 = "[ YY ]"%string.
Parameter ev_tick_EV_3 : nat.
Axiom ev_tick_EV_3_val : ev_tick_EV_3 = 3.
Axiom causal_EV_2_EV_3 : ev_tick_EV_2 <= ev_tick_EV_3.
Parameter assign_EV_3 : Val.
Axiom assign_EV_3_val : assign_EV_3 = "[ Y ]"%string.
Parameter ev_tick_EV_4 : nat.
Axiom ev_tick_EV_4_val : ev_tick_EV_4 = 4.
Axiom causal_EV_3_EV_4 : ev_tick_EV_3 <= ev_tick_EV_4.
Parameter emit_EV_4 : string.
Axiom emit_EV_4_val : emit_EV_4 = "CORTEX_INIT"%string.
Parameter ev_tick_EV_5 : nat.
Axiom ev_tick_EV_5_val : ev_tick_EV_5 = 5.
Axiom causal_EV_4_EV_5 : ev_tick_EV_4 <= ev_tick_EV_5.
Parameter after_EV_5 : nat.
Axiom after_EV_5_val : after_EV_5 = 2.
Parameter ev_tick_EV_7 : nat.
Axiom ev_tick_EV_7_val : ev_tick_EV_7 = 7.
Axiom causal_EV_5_EV_7 : ev_tick_EV_5 <= ev_tick_EV_7.
Parameter emit_EV_7 : string.
Axiom emit_EV_7_val : emit_EV_7 = "AGENT_MITOSIS_SPAWN"%string.
Parameter ev_tick_EV_8 : nat.
Axiom ev_tick_EV_8_val : ev_tick_EV_8 = 8.
Axiom causal_EV_7_EV_8 : ev_tick_EV_7 <= ev_tick_EV_8.
Parameter after_EV_8 : nat.
Axiom after_EV_8_val : after_EV_8 = 1.
Parameter ev_tick_EV_9 : nat.
Axiom ev_tick_EV_9_val : ev_tick_EV_9 = 9.
Axiom causal_EV_8_EV_9 : ev_tick_EV_8 <= ev_tick_EV_9.
Parameter emit_EV_9 : string.
Axiom emit_EV_9_val : emit_EV_9 = "SYSTEM_HALT"%string.

End Babylon60.
