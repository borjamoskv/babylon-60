;;; -*- Mode: LISP; Syntax: COMMON-LISP; Package: LISP-ENGINE.COLLISION; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(in-package :lisp-engine.collision)

;; Cargar el módulo de sockets nativo de SBCL
(eval-when (:compile-toplevel :load-toplevel :execute)
  (require :sb-bsd-sockets))

(defvar *ipc-server-socket* nil)
(defvar *ipc-server-thread* nil)
(defvar *ipc-active-connections* nil)
(defvar *ipc-running-p* nil)

(defun handle-ipc-client (client-stream)
  (declare (type stream client-stream)
           (optimize (speed 3) (safety 0)))
  (handler-case
      (loop while *ipc-running-p* do
           (let ((line (read-line client-stream nil :eof)))
             (if (eq line :eof)
                 (return)
                 (let ((trimmed (string-trim (quote (#\Space #\Tab #\Newline #\Return)) line)))
                   (unless (string= trimmed "")
                     ;; Enviar respuesta en formato JSON plano sin dependencias externas
                     (write-line "{\"status\":\"acknowledged\"}" client-stream)
                     (force-output client-stream))))))
    (error (e)
      (format t "⚠️ IPC client error: ~A~%" e)
      (close client-stream))))

(defun start-collision-ipc-server (&key (host "127.0.0.1") (port 59099))
  (declare (type string host)
           (type fixnum port))
  (when *ipc-running-p*
    (format t "⚠️ Collision IPC Server already running.~%")
    (return-from start-collision-ipc-server nil))
  
  (setf *ipc-running-p* t)
  (setf *ipc-active-connections* nil)
  
  (let ((socket (make-instance (quote sb-bsd-sockets:inet-socket) :type :stream :protocol :tcp))
        (ip-vector (if (string= host "127.0.0.1") #(127 0 0 1) #(0 0 0 0))))
    (setf (sb-bsd-sockets:sockopt-reuse-address socket) t)
    (sb-bsd-sockets:socket-bind socket ip-vector port)
    (sb-bsd-sockets:socket-listen socket 5)
    (setf *ipc-server-socket* socket)
    
    (setf *ipc-server-thread*
          (sb-thread:make-thread
           (lambda ()
             (unwind-protect
                  (loop while *ipc-running-p* do
                       (handler-case
                            ;; Esperar conexión entrante (bloqueante con timeout emulado mediante select/non-blocking o control directo)
                            (let* ((client-socket (sb-bsd-sockets:socket-accept *ipc-server-socket*))
                                   (client-stream (sb-bsd-sockets:socket-make-stream client-socket :input t :output t :buffering :none)))
                              (push client-socket *ipc-active-connections*)
                              (sb-thread:make-thread
                               (lambda ()
                                 (unwind-protect
                                      (handle-ipc-client client-stream)
                                   (sb-bsd-sockets:socket-close client-socket)
                                   (setf *ipc-active-connections* (remove client-socket *ipc-active-connections*))))
                               :name "Collision IPC Client Handler"))
                         (error (e)
                           (when *ipc-running-p*
                             (format t "⚠️ Server accept error: ~A~%" e)))))
               (sb-bsd-sockets:socket-close *ipc-server-socket*)
               (setf *ipc-server-socket* nil)
               (setf *ipc-running-p* nil)))
           :name "Collision IPC Server Thread"))
    
    (format t "Bridge: Collision IPC Server started on ~A:~D (C5-REAL via sb-bsd-sockets)~%" host port)
    t))

(defun stop-collision-ipc-server ()
  (unless *ipc-running-p*
    (format t "⚠️ Collision IPC Server is not running.~%")
    (return-from stop-collision-ipc-server nil))
  
  (setf *ipc-running-p* nil)
  ;; Cerrar todas las conexiones activas
  (dolist (conn *ipc-active-connections*)
    (ignore-errors (sb-bsd-sockets:socket-close conn)))
  (setf *ipc-active-connections* nil)
  
  ;; Cerrar socket principal
  (when *ipc-server-socket*
    (ignore-errors (sb-bsd-sockets:socket-close *ipc-server-socket*))
    (setf *ipc-server-socket* nil))
  
  (when *ipc-server-thread*
    (sb-thread:terminate-thread *ipc-server-thread*)
    (setf *ipc-server-thread* nil))
  
  (format t "🔌 Collision IPC Server stopped cleanly.~%")
  t)
