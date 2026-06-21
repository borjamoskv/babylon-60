namespace Cortex.Kernel

open Fable.Core
open Cortex.Kernel.Babylon

type MaxwellDemon(similarityThreshold: uint16<distance>) =
    let mutable threshold = similarityThreshold

    member this.SetState(state: string) =
        match state.ToUpper() with
        | "ULTRATHINK" -> threshold <- 10us<distance>
        | "CONSTRUCT" -> threshold <- 50us<distance>
        | _ -> threshold <- 150us<distance>

    // Simulate C5-REAL DB causal extraction using bits of the hashes
    member this.CosineSimilarity (id1: uint32, id2: uint32) : uint16<distance> =
        let diff = id1 ^^^ id2
        let ancestry = uint16 (diff % 5u)
        let ledger = uint16 (id1 % 3u)
        let witness = 0us
        let temporal = 5us
        
        causalDistance ancestry ledger witness temporal

    member this.PurgeRedundant (chunks: (uint32 * string) array) =
        let mutable accepted = []
        let mutable purgedCount = 0

        for (h, chunk) in chunks do
            let isRedundant = 
                accepted 
                |> List.exists (fun (acc_h, _) ->
                    let sim = this.CosineSimilarity(h, acc_h)
                    sim <= threshold
                )
            
            if isRedundant then
                purgedCount <- purgedCount + 1
            else
                accepted <- (h, chunk) :: accepted

        let acceptedChunks = accepted |> List.rev |> List.map snd |> List.toArray
        (acceptedChunks, purgedCount)
