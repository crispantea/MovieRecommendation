accesslog = "-"        # "-" means stdout
errorlog = "-"         # "-" means stderr
loglevel = "info"      # debug | info | warning | error | critical
capture_output = True  # redirect print() / stdout / stderr into the error log

worker_class = "gthread"
workers = 2
threads = 50
timeout = 600