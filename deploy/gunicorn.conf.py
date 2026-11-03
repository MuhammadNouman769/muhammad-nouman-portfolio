import multiprocessing
bind = "0.0.0.0:8000"
workers = max(2, multiprocessing.cpu_count() * 2 + 1)
threads = 2
timeout = 30
accesslog = "-"
errorlog = "-"
