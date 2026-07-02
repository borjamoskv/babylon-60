;;; -*- Mode: LISP; Syntax: COMMON-LISP; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(asdf:defsystem :lisp-collision-engine
  :description "C5-REAL High-Performance Dynamic Collision Engine in Common Lisp for SBCL"
  :author "borjamoskv"
  :license "Apache-2.0"
  :version "1.0.0"
  :serial t
  :depends-on () ; Cero dependencias externas para garantizar portabilidad absoluta
  :components ((:file "package")
               (:file "types")
               (:file "primitives")
               (:file "bvh")
               (:file "ipc"))
  :in-order-to ((asdf:test-op (asdf:test-op :lisp-collision-engine/tests))))

(asdf:defsystem :lisp-collision-engine/tests
  :description "Tests for lisp-collision-engine"
  :author "borjamoskv"
  :license "Apache-2.0"
  :depends-on (:lisp-collision-engine)
  :components ((:file "tests"))
  :perform (asdf:test-op (op c)
                         (uiop:symbol-call :lisp-engine.collision :run-collision-tests)))
