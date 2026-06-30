; Modelo SMT-LIB2 para verificación Bounded de BFTNodeState
; Definición estricta de la regla de no-doble-firma criptográfica

(declare-sort Height 0)
(declare-sort NodeID 0)

; Atributos del estado del nodo
(declare-fun isHonest (NodeID) Bool)
(declare-fun hasVoted (NodeID Height) Bool)
(declare-fun voteCount (NodeID Height) Int)

; Axioma: Un nodo honesto jamás emite más de 1 voto por altura criptográfica
(assert (forall ((n NodeID) (h Height))
  (=> (isHonest n) (<= (voteCount n h) 1))))

; Axioma de enlace lógico
(assert (forall ((n NodeID) (h Height))
  (= (hasVoted n h) (> (voteCount n h) 0))))

; --- ASERCIÓN ADVERSARIAL (BÚSQUEDA DE CONTRAEJEMPLOS) ---
; Tratamos de demostrar satisfacibilidad (SAT) para un estado donde un nodo 
; honesto emita 2 o más votos.
(declare-const targetNode NodeID)
(declare-const targetHeight Height)

(assert (isHonest targetNode))
(assert (> (voteCount targetNode targetHeight) 1))

(check-sat)