namespace Cortex.Kernel

open Fable.Core

[<Measure>] type distance

module Babylon =

    let MAX_DIVERGENCE = 1000us

    let causalDistance (ancestryOverlap: uint16) (ledgerOverlap: uint16) (witnessOverlap: uint16) (temporalOverlap: uint16) : uint16<distance> =
        let ancestryWeight = 60us
        let witnessWeight = 30us
        let ledgerWeight = 10us
        let temporalWeight = 1us

        let score = 
            (ancestryOverlap * ancestryWeight) +
            (witnessOverlap * witnessWeight) +
            (ledgerOverlap * ledgerWeight) +
            (temporalOverlap * temporalWeight)

        let dist = 
            if score > MAX_DIVERGENCE then 0us
            else MAX_DIVERGENCE - score

        dist * 1us<distance>

    // Merkle Rollup Deterministic Hash using FNV-1a (32-bit for POC)
    let hashDistanceRollup (rootHash: uint32) (distances: uint16<distance> array) : uint32 =
        let FNV_PRIME = 16777619u
        let mutable currentHash = rootHash
        for d in distances do
            currentHash <- currentHash ^^^ (uint32 d)
            currentHash <- currentHash * FNV_PRIME
        currentHash
