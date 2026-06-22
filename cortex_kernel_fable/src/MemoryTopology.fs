// =========================================================================
// AUTHOR: Borja Moskv (borjamoskv)
// SYSTEM: MOSKV-1 APEX KERNEL
// LEVEL: C5-REAL
// PURPOSE: Immutable Epistemic Graph and Cognitive State Transitions (FSM)
// =========================================================================

namespace Cortex.Kernel

open System
open System
open Cortex.Kernel.StateMachine
open Cortex.Kernel.CausalEngine

module MemoryTopology =

    type EpistemicGraph = Map<Hash256, EpistemicNode>

    // Immutable Cognitive State
    [<Struct>]
    type CognitiveState = {
        Tick: uint64
        Machine: MachineState
        EntropyThreshold: uint16<distance>
        Graph: EpistemicGraph
        GlobalConfidence: Fixed60
    }

    // Genesis constructor
    let genesis (initialThreshold: uint16<distance>) : CognitiveState =
        {
            Tick = 0UL
            Machine = {
                Phase = Observation
                Cycle = 0u
                ExergyAccum = 0u
                TraceHash = 0u
            }
            EntropyThreshold = initialThreshold
            Graph = Map.empty
            GlobalConfidence = Fixed60(0L)
        }

    // Pure Transition Engine: F(State, Stimulus, Exergy) -> State'
    let applyTick (state: CognitiveState) (stimulus: Option<Hash256 * EpistemicNode>) (exergyInput: uint32) : CognitiveState =
        // 1. Advance the pure State Machine
        let nextMachine = StateMachine.stepMachine state.Machine exergyInput

        // 2. Mathematical Maxwell Demon (Pure Thermodynamic Filtering)
        let (nextGraph, confidenceDelta) =
            match stimulus with
            | Some (hash, node) ->
                let isRedundant =
                    state.Graph
                    |> Map.exists (fun existingHash _ ->
                        let (a, b, c, d) = hash
                        let (e, f, g, h) = existingHash
                        let xorPart = a ^^^ e
                        let bits = CausalEngine.popCount xorPart
                        let dist = CausalEngine.causalDistance (uint16 bits) 0us 0us
                        dist <= state.EntropyThreshold
                    )

                if isRedundant then
                    // Redundancy detected: state.Graph remains unchanged, zero confidence delta
                    (state.Graph, Fixed60(0L))
                else
                    // Integrate new knowledge into a new AVL Map node
                    let newGraph = Map.add hash node state.Graph

                    // Compute global confidence increment using Fixed60
                    let delta =
                        match node with
                        | StochasticConjecture (_, conf) ->
                            let confFixed = Fixed60(int64 conf)
                            let hundred = Fixed60(100L)
                            FixedPoint60.div confFixed hundred
                        | VerifiedHash _ ->
                            Fixed60(1L)
                        | VoidAnergy ->
                            Fixed60(0L)

                    (newGraph, delta)

            | None ->
                (state.Graph, Fixed60(0L))

        // 3. Construct the new immutable universe state
        {
            Tick = state.Tick + 1UL
            Machine = nextMachine
            EntropyThreshold = state.EntropyThreshold
            Graph = nextGraph
            GlobalConfidence = FixedPoint60.add state.GlobalConfidence confidenceDelta
        }
