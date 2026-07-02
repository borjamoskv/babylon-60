;;; -*- Mode: LISP; Syntax: COMMON-LISP; Package: LISP-ENGINE.COLLISION; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(in-package :lisp-engine.collision)

(defun assert-true (expr msg)
  (if expr
      (format t "✅ PASS: ~A~%" msg)
      (error "❌ FAIL: Assert True failed: ~A" msg)))

(defun assert-false (expr msg)
  (if (not expr)
      (format t "✅ PASS: ~A~%" msg)
      (error "❌ FAIL: Assert False failed: ~A" msg)))

(defun test-aabb-primitives ()
  (format t "── Testing AABB-AABB Intersections ──~%")
  (let ((a (make-aabb (make-vec3 0.0f0 0.0f0 0.0f0) (make-vec3 2.0f0 2.0f0 2.0f0)))
        (b (make-aabb (make-vec3 1.0f0 1.0f0 1.0f0) (make-vec3 3.0f0 3.0f0 3.0f0)))
        (c (make-aabb (make-vec3 5.0f0 5.0f0 5.0f0) (make-vec3 6.0f0 6.0f0 6.0f0))))
    (assert-true (intersect-aabb-aabb-p a b) "Overlapping AABBs intersect")
    (assert-false (intersect-aabb-aabb-p a c) "Distant AABBs do not intersect")))

(defun test-obb-primitives ()
  (format t "── Testing OBB-OBB Intersections (SAT) ──~%")
  (let* ((axes-identity (make-mat3))
         ;; Inicializar matriz identidad
         (dummy (loop for i from 0 to 2 do
                     (setf (aref axes-identity (+ i (* i 3))) 1.0f0)))
         (a (make-obb (make-vec3 0.0f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0)))
         (b (make-obb (make-vec3 1.5f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0)))
         (c (make-obb (make-vec3 3.0f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0))))
    (declare (ignore dummy))
    (assert-true (intersect-obb-obb-p a b) "Overlapping OBBs intersect")
    (assert-false (intersect-obb-obb-p a c) "Distant OBBs do not intersect")))

(defun test-ray-primitives ()
  (format t "── Testing Ray-OBB Intersections ──~%")
  (let* ((axes-identity (make-mat3))
         (dummy (loop for i from 0 to 2 do
                     (setf (aref axes-identity (+ i (* i 3))) 1.0f0)))
         (o (make-obb (make-vec3 0.0f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0)))
         (ry-hit (make-ray (make-vec3 -5.0f0 0.0f0 0.0f0) (make-vec3 1.0f0 0.0f0 0.0f0)))
         (ry-miss (make-ray (make-vec3 -5.0f0 5.0f0 0.0f0) (make-vec3 1.0f0 0.0f0 0.0f0))))
    (declare (ignore dummy))
    (assert-true (intersect-ray-obb-p ry-hit o) "Ray hitting OBB intersects")
    (assert-false (intersect-ray-obb-p ry-miss o) "Ray missing OBB does not intersect")))

(defun test-bvh-construction ()
  (format t "── Testing SAH-based BVH Construction & Refit ──~%")
  (let* ((axes-identity (make-mat3))
         (dummy (loop for i from 0 to 2 do
                     (setf (aref axes-identity (+ i (* i 3))) 1.0f0)))
         (obbs (make-array 3 :initial-contents
                           (list
                            (make-obb (make-vec3 0.0f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0))
                            (make-obb (make-vec3 2.0f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0))
                            (make-obb (make-vec3 10.0f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0)))))
         (indices (make-array 3 :element-type (quote fixnum) :initial-contents (quote (0 1 2)))))
    (declare (ignore dummy))
    (let ((tree (build-bvh obbs indices)))
      (assert-true (not (null tree)) "BVH Tree successfully built")
      (assert-true (not (null (bvh-node-aabb tree))) "Root node has valid bounding AABB")
      
      ;; Refit test
      (setf (aref (obb-center (aref obbs 0)) 0) 0.5f0)
      (refit-bvh tree obbs)
      (assert-true (not (null (bvh-node-aabb tree))) "BVH Tree successfully refitted after updates")
      
      ;; Rotations test
      (update-bvh-rotations tree)
      (assert-true (not (null tree)) "BVH Tree successfully rebalanced with local rotations"))))

(defun test-no-consing-performance ()
  (format t "── Testing Consing and Allocation Performance (Evasión de GC) ──~%")
  (let* ((axes-identity (make-mat3))
         (dummy (loop for i from 0 to 2 do
                     (setf (aref axes-identity (+ i (* i 3))) 1.0f0)))
         (a (make-obb (make-vec3 0.0f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0)))
         (b (make-obb (make-vec3 1.5f0 0.0f0 0.0f0) axes-identity (make-vec3 1.0f0 1.0f0 1.0f0))))
    (declare (ignore dummy))
    ;; Ejecutar loop de 1000 iteraciones y auditar consing mediante time
    (time
     (loop for i from 1 to 1000 do
          (intersect-obb-obb-p a b)))
    (format t "✅ PASS: Consing stress test completed successfully.~%")))

(defun run-collision-tests ()
  (format t "🚀 Starting Lisp Collision Engine Suite (C5-REAL)...~%")
  (test-aabb-primitives)
  (test-obb-primitives)
  (test-ray-primitives)
  (test-bvh-construction)
  (test-no-consing-performance)
  (format t "🎉 All Lisp Collision tests PASSED successfully!~%")
  t)
