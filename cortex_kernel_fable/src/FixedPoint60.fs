namespace Cortex.Kernel

open System

// -------------------------------------------------------------------------
// [BABYLON-60] INVARIANT III: Strict Float64 Eradication
// Scale S = 60^3 = 216,000 (Degrees, Minutes, Seconds, Thirds)
// -------------------------------------------------------------------------

[<Struct>]
type Fixed60 =
    val Value: int64
    new(v: int64) = { Value = v }

    // --- Formateador Lexical Sexagesimal ---
    override this.ToString() =
        let isNeg = this.Value < 0L
        let absVal = Math.Abs(this.Value)
        let deg = absVal / 216000L
        let rem1 = absVal % 216000L
        let min = rem1 / 3600L
        let rem2 = rem1 % 3600L
        let sec = rem2 / 60L
        let thirds = rem2 % 60L
        let sign = if isNeg then "-" else ""
        sprintf "%s%d°%02d'%02d\"%02d'''" sign deg min sec thirds

[<RequireQualifiedAccess>]
module FixedPoint60 =
    let [<Literal>] Scale = 216000L
    let ScaleBig = bigint 216000

    // --- Constructor Estructural ---
    let create (deg: int) (min: int) (sec: int) (thirds: int) =
        let sign = if deg < 0 || min < 0 || sec < 0 || thirds < 0 then -1L else 1L
        let raw = (int64 (abs deg) * Scale) + (int64 (abs min) * 3600L) + (int64 (abs sec) * 60L) + int64 (abs thirds)
        Fixed60(raw * sign)

    // --- Invariante I: Aritmética Plana de Hardware ---
    let add (a: Fixed60) (b: Fixed60) = Fixed60(a.Value + b.Value)
    let sub (a: Fixed60) (b: Fixed60) = Fixed60(a.Value - b.Value)

    // --- Invariante III & IV: Prevención de Overflow (BigInt Cast) ---
    let mul (a: Fixed60) (b: Fixed60) =
        let bigA = bigint a.Value
        let bigB = bigint b.Value
        // Resolución matemática segura en el host anfitrión antes del truncamiento
        let result = (bigA * bigB) / ScaleBig
        Fixed60(int64 result)

    let div (a: Fixed60) (b: Fixed60) =
        if b.Value = 0L then raise (DivideByZeroException("BABYLON-60 FATAL: División por cero prevenida."))
        let bigA = bigint a.Value
        let bigB = bigint b.Value
        // Elevación de escala del dividendo previo al cociente (resolución simétrica)
        let result = (bigA * ScaleBig) / bigB
        Fixed60(int64 result)
