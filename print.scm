;; $Id: print.scm,v 1.4 2007/04/21 22:02:13 mike Exp $
;;
;; This file may be used to print gschem schematics from the
;; command line.  Typical usage is:
;;
;;   gschem -p -o mysch.ps -s /path/to/this/file/print.scm mysch.sch
;;
;; The schematic in "mysch.sch" will be printed to the file "mysch.ps"

;; Uncomment these to override defaults when printing from the command line
;(output-orientation "portrait")
(output-type "limits")
;(output-color "enabled")
;(output-text "ps")

; You need call this after you call any rc file function
(gschem-use-rc-values)

; filename is specified on the command line
(gschem-postscript "dummyfilename")

(gschem-exit)
