;;; -*- Mode: LISP; Syntax: COMMON-LISP; Package: CL-USER; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(in-package :cl-user)

(defpackage :lisp-engine.collision
  (:use :cl)
  (:export
   ;; Tipos y Vectorización
   #:vec3
   #:mat3
   #:make-vec3
   #:make-mat3
   
   ;; Estructuras de Colisión
   #:aabb
   #:make-aabb
   #:aabb-min
   #:aabb-max
   
   #:obb
   #:make-obb
   #:obb-center
   #:obb-axes
   #:obb-extents
   
   #:ray
   #:make-ray
   #:ray-origin
   #:ray-direction
   
   #:bvh-node
   #:make-bvh-node
   #:bvh-node-aabb
   #:bvh-node-left
   #:bvh-node-right
   #:bvh-node-obb-indices
   
   ;; Primitivas de Intersección
   #:intersect-aabb-aabb-p
   #:intersect-obb-obb-p
   #:intersect-ray-obb-p
   
   ;; Jerarquía BVH
   #:build-bvh
   #:refit-bvh
   #:update-bvh-rotations
   
   ;; IPC
   #:start-collision-ipc-server
   #:stop-collision-ipc-server))
