;;; -*- Mode: LISP; Syntax: COMMON-LISP; Package: LISP-ENGINE.COLLISION; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(in-package :lisp-engine.collision)

;; Definiciones de tipos vectoriales para optimización de SBCL
(deftype vec3 () (quote (simple-array single-float (3))))
(deftype mat3 () (quote (simple-array single-float (9))))

;; Constructor inline para vectores 3D sin consing (unboxed single-floats)
(declaim (inline make-vec3))
(defun make-vec3 (&optional (x 0.0f0) (y 0.0f0) (z 0.0f0))
  (declare (type single-float x y z)
           (optimize (speed 3) (safety 0)))
  (let ((v (make-array 3 :element-type (quote single-float))))
    (setf (aref v 0) x)
    (setf (aref v 1) y)
    (setf (aref v 2) z)
    v))

;; Constructor inline para matrices 3x3 planas en memoria
(declaim (inline make-mat3))
(defun make-mat3 ()
  (declare (optimize (speed 3) (safety 0)))
  (make-array 9 :element-type (quote single-float) :initial-element 0.0f0))

;; Estructura AABB (Axis-Aligned Bounding Box)
(defstruct (aabb
             (:constructor %make-aabb (min max)))
  (min (make-vec3) :type vec3 :read-only t)
  (max (make-vec3) :type vec3 :read-only t))

(declaim (inline make-aabb))
(defun make-aabb (min-vec max-vec)
  (declare (type vec3 min-vec max-vec)
           (optimize (speed 3) (safety 0)))
  (%make-aabb min-vec max-vec))

;; Estructura OBB (Oriented Bounding Box)
(defstruct (obb
             (:constructor %make-obb (center axes extents)))
  (center (make-vec3) :type vec3 :read-only t)
  (axes (make-mat3) :type mat3 :read-only t) ; Matriz de rotación 3x3 plana
  (extents (make-vec3) :type vec3 :read-only t))

(declaim (inline make-obb))
(defun make-obb (center-vec axes-mat extents-vec)
  (declare (type vec3 center-vec extents-vec)
           (type mat3 axes-mat)
           (optimize (speed 3) (safety 0)))
  (%make-obb center-vec axes-mat extents-vec))

;; Estructura Ray
(defstruct (ray
             (:constructor %make-ray (origin direction)))
  (origin (make-vec3) :type vec3 :read-only t)
  (direction (make-vec3) :type vec3 :read-only t))

(declaim (inline make-ray))
(defun make-ray (origin-vec direction-vec)
  (declare (type vec3 origin-vec direction-vec)
           (optimize (speed 3) (safety 0)))
  (%make-ray origin-vec direction-vec))

;; Estructura bvh-node para el árbol jerárquico
(defstruct bvh-node
  (aabb nil :type (or null aabb))
  (left nil :type (or null bvh-node))
  (right nil :type (or null bvh-node))
  (obb-indices nil :type (or null (simple-array fixnum (*)))))
