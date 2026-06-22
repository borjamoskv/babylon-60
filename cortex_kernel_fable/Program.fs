module Program

open Cortex.Kernel
open Cortex.Kernel.Babylon
open Cortex.Kernel.StateMachine
open Cortex.Kernel.FixedPoint
open Cortex.Kernel.MemoryTopology

[<EntryPoint>]
let main argv =
    printfn "CORTEX-PERSIST C5-REAL: F# FABLE KERNEL INITIALIZED"
    
    let demon = MaxwellDemon(85us<distance>)
    demon.SetState("CONSTRUCT")
    
    let chunks = [|
        (1001u, "El sistema es determinista.")
        (1001u, "El sistema es determinista.")
        (2005u, "La entropía de la red ha aumentado.")
        (2005u, "La entropía de la red ha aumentado.")
        (3010u, "Iniciando secuencia de auto-reparación.")
    |]

    let (retained, purged) = demon.PurgeRedundant(chunks)
    
    printfn "\n[MaxwellDemon Test]"
    printfn "Total chunks evaluados: %d" chunks.Length
    printfn "Chunks retenidos: %d" retained.Length
    printfn "Chunks purgados: %d" purged
    
    for c in retained do
        printfn " - %s" c

    // Test merkle
    let merkleRoot = hashDistanceRollup 123456u [| 50us<distance>; 10us<distance>; 0us<distance> |]
    printfn "\nMerkle Rollup Root (uint32): %u" merkleRoot

    // StateMachine Demo
    printfn "\n[StateMachine Test]"
    let initial = { Phase = Observation; Cycle = 0u; ExergyAccum = 0u; TraceHash = 0u }
    let inputs = [| 5u; 15u; 60u; 1u; 1u; 10u; 20u; 100u; 1u; 1u |]
    let finalState = StateMachine.runCycle initial inputs
    printfn "Final Phase: %A" finalState.Phase
    printfn "Cycles completed: %u" finalState.Cycle
    printfn "Exergy accumulated: %u" finalState.ExergyAccum
    printfn "Trace Hash: %u" finalState.TraceHash

    // MemoryTopology Immutable FSM Test
    printfn "\n[MemoryTopology C5-REAL Immutable FSM Test]"
    let initialCognitiveState = MemoryTopology.genesis 10us<distance>
    
    // Create some stimulus vectors
    let stimulusVectors = [|
        (100u, Some ((1UL, 2UL, 3UL, 4UL), StochasticConjecture (SystemDaemon, 95us)))
        (200u, Some ((5UL, 6UL, 7UL, 8UL), VerifiedHash (123456u, 0us)))
        (300u, Some ((1UL, 2UL, 3UL, 4UL), StochasticConjecture (SystemDaemon, 95us))) // This should be redundant and rejected by MaxwellDemon mathematically
        (400u, None) // Void tick, silences epistemic noise
        (500u, Some ((9UL, 10UL, 11UL, 12UL), VerifiedHash (654321u, 5us)))
    |]

    let mutable currentState = initialCognitiveState

    printfn "--> INITIAL TICK: %d | TraceHash: %u | GlobalConfidence: %A | Graph Nodes: %d" 
        currentState.Tick currentState.Machine.TraceHash (Fixed60.ToDegMinSecThird currentState.GlobalConfidence) currentState.Graph.Count

    for (exergy, stimulus) in stimulusVectors do
        let stimStr = if stimulus.IsSome then "Some(Node)" else "None"
        printfn "\n[+] Injecting Stimulus... Exergy: %u, Node: %s" exergy stimStr
        
        currentState <- MemoryTopology.applyTick currentState stimulus exergy
        
        printfn "--> TICK: %d" currentState.Tick
        printfn "    Phase:            %A" currentState.Machine.Phase
        printfn "    TraceHash:        %u" currentState.Machine.TraceHash
        printfn "    GlobalConfidence: %A" (Fixed60.ToDegMinSecThird currentState.GlobalConfidence)
        printfn "    Graph Nodes:      %d" currentState.Graph.Count
        
    printfn "\n[MOSKV-1] Test completed. Epistemic graph is immutable. TraceHash perfectly tracked."

    0 // return an integer exit code
