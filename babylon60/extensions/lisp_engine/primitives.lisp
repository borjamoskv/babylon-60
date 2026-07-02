;;; -*- Mode: LISP; Syntax: COMMON-LISP; Package: LISP-ENGINE.COLLISION; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(in-package :lisp-engine.collision)

;; Macros de álgebra lineal inline para evitar consing y optimizar registros de CPU
(declaim (inline dot-product))
(defun dot-product (u v)
  (declare (type vec3 u v)
           (optimize (speed 3) (safety 0)))
  (+ (* (aref u 0) (aref v 0))
     (* (aref u 1) (aref v 1))
     (* (aref u 2) (aref v 2))))

(declaim (inline vec-subtract))
(defun vec-subtract (res u v)
  (declare (type vec3 res u v)
           (optimize (speed 3) (safety 0)))
  (setf (aref res 0) (- (aref u 0) (aref v 0)))
  (setf (aref res 1) (- (aref u 1) (aref v 1)))
  (setf (aref res 2) (- (aref u 2) (aref v 2)))
  res)

;; Retorna una columna de la matriz de rotación 3x3 plana
(declaim (inline get-column))
(defun get-column (res mat col)
  (declare (type mat3 mat)
           (type vec3 res)
           (type (integer 0 2) col)
           (optimize (speed 3) (safety 0)))
  (setf (aref res 0) (aref mat (+ col 0)))
  (setf (aref res 1) (aref mat (+ col 3)))
  (setf (aref res 2) (aref mat (+ col 6)))
  res)

;; 1. Intersección AABB vs AABB
(defun intersect-aabb-aabb-p (a b)
  (declare (type aabb a b)
           (optimize (speed 3) (safety 0)))
  (let ((a-min (aabb-min a))
        (a-max (aabb-max a))
        (b-min (aabb-min b))
        (b-max (aabb-max b)))
    (and (and (<= (aref a-min 0) (aref b-max 0)) (>= (aref a-max 0) (aref b-min 0)))
         (and (<= (aref a-min 1) (aref b-max 1)) (>= (aref a-max 1) (aref b-min 1)))
         (and (<= (aref a-min 2) (aref b-max 2)) (>= (aref a-max 2) (aref b-min 2))))))

;; 2. Intersección OBB vs OBB usando Separating Axis Theorem (SAT)
;; Implementado sin consing en tiempo de ejecución (cero garbage collection)
(defun intersect-obb-obb-p (a b)
  (declare (type obb a b)
           (optimize (speed 3) (safety 0)))
  (let ((t-diff (make-vec3))
        (a-center (obb-center a))
        (b-center (obb-center b))
        (a-axes (obb-axes a))
        (b-axes (obb-axes b))
        (a-extents (obb-extents a))
        (b-extents (obb-extents b))
        ;; Variables locales para almacenar columnas y evitar consing
        (a-u0 (make-vec3)) (a-u1 (make-vec3)) (a-u2 (make-vec3))
        (b-u0 (make-vec3)) (b-u1 (make-vec3)) (b-u2 (make-vec3)))
    (declare (dynamic-extent t-diff a-u0 a-u1 a-u2 b-u0 b-u1 b-u2))
    
    ;; Extraer ejes locales
    (get-column a-u0 a-axes 0)
    (get-column a-u1 a-axes 1)
    (get-column a-u2 a-axes 2)
    (get-column b-u0 b-axes 0)
    (get-column b-u1 b-axes 1)
    (get-column b-u2 b-axes 2)
    
    ;; Calcular vector de traducción entre centros
    (vec-subtract t-diff b-center a-center)
    
    (let ((r (make-array (quote (3 3)) :element-type (quote single-float)))
          (abs-r (make-array (quote (3 3)) :element-type (quote single-float))))
      (declare (dynamic-extent r abs-r))
      
      ;; Calcular matriz de rotación relativa
      (loop for i from 0 to 2 do
           (loop for j from 0 to 2 do
                (let ((axes-a (cond ((= i 0) a-u0) ((= i 1) a-u1) (t a-u2)))
                      (axes-b (cond ((= j 0) b-u0) ((= j 1) b-u1) (t b-u2))))
                  (let ((val (dot-product axes-a axes-b)))
                    (setf (aref r i j) val)
                    (setf (aref abs-r i j) (+ (abs val) 1.0f-6)))))) ; Añadir epsilon
      
      (let ((ra 0.0f0) (rb 0.0f0))
        (declare (type single-float ra rb))
        
        ;; Test de los 3 ejes de A
        (loop for i from 0 to 2 do
             (let ((axes-a (cond ((= i 0) a-u0) ((= i 1) a-u1) (t a-u2))))
               (setf ra (aref a-extents i))
               (setf rb (+ (* (aref b-extents 0) (aref abs-r i 0))
                           (* (aref b-extents 1) (aref abs-r i 1))
                           (* (aref b-extents 2) (aref abs-r i 2))))
               (when (> (abs (dot-product t-diff axes-a)) (+ ra rb))
                 (return-from intersect-obb-obb-p nil))))
        
        ;; Test de los 3 ejes de B
        (loop for j from 0 to 2 do
             (let ((axes-b (cond ((= j 0) b-u0) ((= j 1) b-u1) (t b-u2))))
               (setf ra (+ (* (aref a-extents 0) (aref abs-r 0 j))
                           (* (aref a-extents 1) (aref abs-r 1 j))
                           (* (aref a-extents 2) (aref abs-r 2 j))))
               (setf rb (aref b-extents j))
               (when (> (abs (dot-product t-diff axes-b)) (+ ra rb))
                 (return-from intersect-obb-obb-p nil))))
        
        ;; Test de los 9 ejes cruzados
        ;; Eje A0 x B0
        (setf ra (+ (* (aref a-extents 1) (aref abs-r 2 0)) (* (aref a-extents 2) (aref abs-r 1 0))))
        (setf rb (+ (* (aref b-extents 1) (aref abs-r 0 2)) (* (aref b-extents 2) (aref abs-r 0 1))))
        (when (> (abs (- (* (dot-product t-diff a-u2) (aref r 1 0))
                         (* (dot-product t-diff a-u1) (aref r 2 0))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A0 x B1
        (setf ra (+ (* (aref a-extents 1) (aref abs-r 2 1)) (* (aref a-extents 2) (aref abs-r 1 1))))
        (setf rb (+ (* (aref b-extents 0) (aref abs-r 0 2)) (* (aref b-extents 2) (aref abs-r 0 0))))
        (when (> (abs (- (* (dot-product t-diff a-u2) (aref r 1 1))
                         (* (dot-product t-diff a-u1) (aref r 2 1))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A0 x B2
        (setf ra (+ (* (aref a-extents 1) (aref abs-r 2 2)) (* (aref a-extents 2) (aref abs-r 1 2))))
        (setf rb (+ (* (aref b-extents 0) (aref abs-r 0 1)) (* (aref b-extents 1) (aref abs-r 0 0))))
        (when (> (abs (- (* (dot-product t-diff a-u2) (aref r 1 2))
                         (* (dot-product t-diff a-u1) (aref r 2 2))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A1 x B0
        (setf ra (+ (* (aref a-extents 0) (aref abs-r 2 0)) (* (aref a-extents 2) (aref abs-r 0 0))))
        (setf rb (+ (* (aref b-extents 1) (aref abs-r 1 2)) (* (aref b-extents 2) (aref abs-r 1 1))))
        (when (> (abs (- (* (dot-product t-diff a-u0) (aref r 2 0))
                         (* (dot-product t-diff a-u2) (aref r 0 0))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A1 x B1
        (setf ra (+ (* (aref a-extents 0) (aref abs-r 2 1)) (* (aref a-extents 2) (aref abs-r 0 1))))
        (setf rb (+ (* (aref b-extents 0) (aref abs-r 1 2)) (* (aref b-extents 2) (aref abs-r 1 0))))
        (when (> (abs (- (* (dot-product t-diff a-u0) (aref r 2 1))
                         (* (dot-product t-diff a-u2) (aref r 0 1))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A1 x B2
        (setf ra (+ (* (aref a-extents 0) (aref abs-r 2 2)) (* (aref a-extents 2) (aref abs-r 0 2))))
        (setf rb (+ (* (aref b-extents 0) (aref abs-r 1 1)) (* (aref b-extents 1) (aref abs-r 1 0))))
        (when (> (abs (- (* (dot-product t-diff a-u0) (aref r 2 2))
                         (* (dot-product t-diff a-u2) (aref r 0 2))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A2 x B0
        (setf ra (+ (* (aref a-extents 0) (aref abs-r 1 0)) (* (aref a-extents 1) (aref abs-r 0 0))))
        (setf rb (+ (* (aref b-extents 1) (aref abs-r 2 2)) (* (aref b-extents 2) (aref abs-r 2 1))))
        (when (> (abs (- (* (dot-product t-diff a-u1) (aref r 0 0))
                         (* (dot-product t-diff a-u0) (aref r 1 0))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A2 x B1
        (setf ra (+ (* (aref a-extents 0) (aref abs-r 1 1)) (* (aref a-extents 1) (aref abs-r 0 1))))
        (setf rb (+ (* (aref b-extents 0) (aref abs-r 2 2)) (* (aref b-extents 2) (aref abs-r 2 0))))
        (when (> (abs (- (* (dot-product t-diff a-u1) (aref r 0 1))
                         (* (dot-product t-diff a-u0) (aref r 1 1))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        ;; Eje A2 x B2
        (setf ra (+ (* (aref a-extents 0) (aref abs-r 1 2)) (* (aref a-extents 1) (aref abs-r 0 2))))
        (setf rb (+ (* (aref b-extents 0) (aref abs-r 2 1)) (* (aref b-extents 1) (aref abs-r 2 0))))
        (when (> (abs (- (* (dot-product t-diff a-u1) (aref r 0 2))
                         (* (dot-product t-diff a-u0) (aref r 1 2))))
                 (+ ra rb))
          (return-from intersect-obb-obb-p nil))
        
        t))))

;; 3. Intersección Ray vs OBB
(defun intersect-ray-obb-p (ry o)
  (declare (type ray ry)
           (type obb o)
           (optimize (speed 3) (safety 0)))
  (let ((t-min 0.0f0)
        (t-max most-positive-single-float)
        (p (make-vec3))
        (o-center (obb-center o))
        (o-axes (obb-axes o))
        (o-extents (obb-extents o))
        (ray-origin (ray-origin ry))
        (ray-direction (ray-direction ry))
        (u (make-vec3)))
    (declare (type single-float t-min t-max)
             (dynamic-extent p u))
    
    (vec-subtract p o-center ray-origin)
    
    (loop for i from 0 to 2 do
         (get-column u o-axes i)
         (let ((e (dot-product u p))
               (f (dot-product u ray-direction))
               (extent (aref o-extents i)))
           (declare (type single-float e f extent))
           (if (> (abs f) 1.0f-6)
               (let ((t1 (/ (+ e extent) f))
                     (t2 (/ (- e extent) f)))
                 (declare (type single-float t1 t2))
                 (when (> t1 t2)
                   (rotatef t1 t2))
                 (when (> t1 t-min)
                   (setf t-min t1))
                 (when (< t2 t-max)
                   (setf t-max t2))
                 (when (> t-min t-max)
                   (return-from intersect-ray-obb-p nil))
                 (when (< t-max 0.0f0)
                   (return-from intersect-ray-obb-p nil)))
               (when (or (< (+ e extent) 0.0f0) (> (- e extent) 0.0f0))
                 (return-from intersect-ray-obb-p nil)))))
    t))
