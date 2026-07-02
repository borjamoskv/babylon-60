;;; -*- Mode: LISP; Syntax: COMMON-LISP; Package: LISP-ENGINE.COLLISION; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(in-package :lisp-engine.collision)

;; Calcula el área superficial de un AABB
(declaim (inline aabb-surface-area))
(defun aabb-surface-area (box)
  (declare (type aabb box)
           (optimize (speed 3) (safety 0)))
  (let* ((min (aabb-min box))
         (max (aabb-max box))
         (dx (- (aref max 0) (aref min 0)))
         (dy (- (aref max 1) (aref min 1)))
         (dz (- (aref max 2) (aref min 2))))
    (declare (type single-float dx dy dz))
    (* 2.0f0 (+ (* dx dy) (* dy dz) (* dz dx)))))

;; Unión de dos AABBs
(defun union-aabb (a b)
  (declare (type aabb a b)
           (optimize (speed 3) (safety 0)))
  (let ((a-min (aabb-min a))
        (a-max (aabb-max a))
        (b-min (aabb-min b))
        (b-max (aabb-max b))
        (r-min (make-vec3))
        (r-max (make-vec3)))
    (declare (dynamic-extent r-min r-max))
    (loop for i from 0 to 2 do
         (setf (aref r-min i) (min (aref a-min i) (aref b-min i)))
         (setf (aref r-max i) (max (aref a-max i) (aref b-max i))))
    (make-aabb (make-vec3 (aref r-min 0) (aref r-min 1) (aref r-min 2))
               (make-vec3 (aref r-max 0) (aref r-max 1) (aref r-max 2)))))

;; Calcula el AABB delimitador para un OBB individual
(defun compute-obb-aabb (o)
  (declare (type obb o)
           (optimize (speed 3) (safety 0)))
  (let ((center (obb-center o))
        (axes (obb-axes o))
        (extents (obb-extents o))
        (r-min (make-vec3))
        (r-max (make-vec3))
        (r (make-vec3)))
    (declare (dynamic-extent r-min r-max r))
    (loop for i from 0 to 2 do
         (let ((val (+ (* (aref extents 0) (abs (aref axes (+ 0 (* i 3)))))
                       (* (aref extents 1) (abs (aref axes (+ 1 (* i 3)))))
                       (* (aref extents 2) (abs (aref axes (+ 2 (* i 3))))))))
           (setf (aref r i) val)))
    (loop for i from 0 to 2 do
         (setf (aref r-min i) (- (aref center i) (aref r i)))
         (setf (aref r-max i) (+ (aref center i) (aref r i))))
    (make-aabb (make-vec3 (aref r-min 0) (aref r-min 1) (aref r-min 2))
               (make-vec3 (aref r-max 0) (aref r-max 1) (aref r-max 2)))))

;; Construcción recursiva del BVH usando Heurística de Área Superficial (SAH)
(defun build-bvh (obbs indices)
  (declare (type (simple-array obb (*)) obbs)
           (type (simple-array fixnum (*)) indices)
           (optimize (speed 3) (safety 0)))
  (let ((n (length indices)))
    (declare (type fixnum n))
    (when (= n 0)
      (return-from build-bvh nil))
    
    ;; Calcular el AABB global del nodo
    (let ((global-aabb (compute-obb-aabb (aref obbs (aref indices 0)))))
      (loop for i from 1 to (1- n) do
           (setf global-aabb (union-aabb global-aabb (compute-obb-aabb (aref obbs (aref indices i))))))
      
      (when (<= n 2)
        (return-from build-bvh
          (make-bvh-node :aabb global-aabb :obb-indices indices)))
      
      ;; Implementación SAH con 12 divisiones (buckets)
      (let ((best-axis -1)
            (best-split 0.0f0)
            (best-cost most-positive-single-float)
            (min-bounds (aabb-min global-aabb))
            (max-bounds (aabb-max global-aabb)))
        
        (loop for axis from 0 to 2 do
             (let ((axis-min (aref min-bounds axis))
                   (axis-max (aref max-bounds axis)))
               (declare (type single-float axis-min axis-max))
               (when (> (- axis-max axis-min) 1.0f-5)
                 (let ((scale (/ 12.0f0 (- axis-max axis-min))))
                   (declare (type single-float scale))
                   
                   ;; Inicializar buckets
                   (let ((bucket-count (make-array 12 :element-type (quote fixnum) :initial-element 0))
                         (bucket-aabbs (make-array 12 :initial-element nil)))
                     
                     (loop for idx across indices do
                          (let* ((o (aref obbs idx))
                                 (c (obb-center o))
                                 (b-idx (floor (* (- (aref c axis) axis-min) scale))))
                            (declare (type fixnum b-idx))
                            (let ((b-clamped (max 0 (min 11 b-idx))))
                              (incf (aref bucket-count b-clamped))
                              (let ((obb-aabb (compute-obb-aabb o)))
                                (setf (aref bucket-aabbs b-clamped)
                                      (if (aref bucket-aabbs b-clamped)
                                          (union-aabb (aref bucket-aabbs b-clamped) obb-aabb)
                                          obb-aabb))))))
                     
                     ;; Evaluar divisiones SAH
                     (loop for split-idx from 1 to 10 do
                          (let ((left-aabb nil)
                                (right-aabb nil)
                                (left-count 0)
                                (right-count 0))
                            (declare (type fixnum left-count right-count))
                            
                            ;; Lado izquierdo
                            (loop for i from 0 to (1- split-idx) do
                                 (when (> (aref bucket-count i) 0)
                                   (incf left-count (aref bucket-count i))
                                   (setf left-aabb
                                         (if left-aabb
                                             (union-aabb left-aabb (aref bucket-aabbs i))
                                             (aref bucket-aabbs i)))))
                            
                            ;; Lado derecho
                            (loop for i from split-idx to 11 do
                                 (when (> (aref bucket-count i) 0)
                                   (incf right-count (aref bucket-count i))
                                   (setf right-aabb
                                         (if right-aabb
                                             (union-aabb right-aabb (aref bucket-aabbs i))
                                             (aref bucket-aabbs i)))))
                            
                            (when (and left-aabb right-aabb)
                              (let ((cost (+ 0.1f0 ; Costo de travesía
                                             (* (/ (aabb-surface-area left-aabb) (aabb-surface-area global-aabb))
                                                (coerce left-count (quote single-float)))
                                             (* (/ (aabb-surface-area right-aabb) (aabb-surface-area global-aabb))
                                                (coerce right-count (quote single-float))))))
                                (declare (type single-float cost))
                                (when (< cost best-cost)
                                  (setf best-cost cost)
                                  (setf best-axis axis)
                                  (setf best-split (+ axis-min (/ (coerce split-idx (quote single-float)) scale)))))))))))))
        
        ;; Si no encontramos división que mejore el costo de hoja, hacer hoja
        (if (or (= best-axis -1) (>= best-cost (coerce n (quote single-float))))
            (make-bvh-node :aabb global-aabb :obb-indices indices)
            ;; De lo contrario, dividir y recurrir
            (let ((left-indices (make-array n :element-type (quote fixnum) :fill-pointer 0))
                  (right-indices (make-array n :element-type (quote fixnum) :fill-pointer 0)))
              (loop for idx across indices do
                   (let* ((o (aref obbs idx))
                          (c (obb-center o)))
                     (if (< (aref c best-axis) best-split)
                         (vector-push idx left-indices)
                         (vector-push idx right-indices))))
              
              (let ((left-arr (make-array (length left-indices) :element-type (quote fixnum) :initial-contents left-indices))
                    (right-arr (make-array (length right-indices) :element-type (quote fixnum) :initial-contents right-indices)))
                (make-bvh-node
                 :aabb global-aabb
                 :left (build-bvh obbs left-arr)
                 :right (build-bvh obbs right-arr)))))))))

;; Algoritmo de Refit ascendente recursivo (actualiza AABBs en cada frame)
(defun refit-bvh (node obbs)
  (declare (type bvh-node node)
           (type (simple-array obb (*)) obbs)
           (optimize (speed 3) (safety 0)))
  (cond
    ;; Nodo hoja
    ((bvh-node-obb-indices node)
     (let* ((indices (bvh-node-obb-indices node))
            (first-aabb (compute-obb-aabb (aref obbs (aref indices 0)))))
       (loop for i from 1 to (1- (length indices)) do
            (setf first-aabb (union-aabb first-aabb (compute-obb-aabb (aref obbs (aref indices i))))))
       (setf (bvh-node-aabb node) first-aabb)))
    ;; Nodo intermedio
    (t
     (let ((left-child (bvh-node-left node))
           (right-child (bvh-node-right node)))
       (when left-child (refit-bvh left-child obbs))
       (when right-child (refit-bvh right-child obbs))
       (when (and left-child right-child)
         (setf (bvh-node-aabb node)
               (union-aabb (bvh-node-aabb left-child)
                           (bvh-node-aabb right-child))))))))

;; Rotaciones locales de nodos del BVH para rebalanceo dinámico
(defun update-bvh-rotations (node)
  (declare (type bvh-node node)
           (optimize (speed 3) (safety 0)))
  (when (or (null node) (bvh-node-obb-indices node))
    (return-from update-bvh-rotations nil))
  
  (let ((l (bvh-node-left node))
        (r (bvh-node-right node)))
    (when l (update-bvh-rotations l))
    (when r (update-bvh-rotations r))
    
    ;; Evaluar balanceo SAH local y rotar nodos si mejora la superficie
    (when (and l r (not (bvh-node-obb-indices l)) (not (bvh-node-obb-indices r)))
      (let* ((area-ll (if (bvh-node-left l) (aabb-surface-area (bvh-node-aabb (bvh-node-left l))) 0.0f0))
             (area-lr (if (bvh-node-right l) (aabb-surface-area (bvh-node-aabb (bvh-node-right l))) 0.0f0))
             (area-rl (if (bvh-node-left r) (aabb-surface-area (bvh-node-aabb (bvh-node-left r))) 0.0f0))
             (area-rr (if (bvh-node-right r) (aabb-surface-area (bvh-node-aabb (bvh-node-right r))) 0.0f0))
             (current-cost (+ area-ll area-lr area-rl area-rr)))
        (declare (type single-float area-ll area-lr area-rl area-rr current-cost))
        
        ;; Rotación simple izquierda-derecha si reduce el costo
        (when (and (bvh-node-left l) (bvh-node-left r))
          (let ((test-cost (+ area-ll (aabb-surface-area (bvh-node-aabb (bvh-node-left r))) area-lr area-rr)))
            (when (< test-cost (* current-cost 0.85f0)) ; Rotar si hay mejora del 15%
              (rotatef (bvh-node-right l) (bvh-node-left r))
              (setf (bvh-node-aabb l) (union-aabb (bvh-node-aabb (bvh-node-left l)) (bvh-node-aabb (bvh-node-right l))))
              (setf (bvh-node-aabb r) (union-aabb (bvh-node-aabb (bvh-node-left r)) (bvh-node-aabb (bvh-node-right r)))))))))))
