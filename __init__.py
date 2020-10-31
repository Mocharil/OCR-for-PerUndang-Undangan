"""
this module can applyed with ray

class Pdf : processing OCR Pdf into Json

class Lookup : function for extraction data from OCR result

class Ocr_pdf : Processig OCR Pdf into text
"""
import aril2
__dirname__ = aril2.__path__[0]
__version__ = "0.2"
__author__ = "aril"
__github__ = "https://github.com/Mocharil"
__example__ = """example using ray
import os
import ray
from ray.util import ActorPool
from aril2 import Ocr_pdf
ray.init(webui_host='0.0.0.0')
# proses membuat class jadi ray actor
Ocr_pdf = ray.remote(Ocr_pdf)

# proses assign worker ke ray actor
# num_cpus itu untuk kasih tau ray worker itu pakai berapa core
# parameter i di dalam remote itu sesuai dengan init dari Ocr_pdf
# i berguna untuk menentukan core apa yang dipakai worker itu
# misal i=[0,1,2] artinya worker itu pakai core id 0, 1, dan 2 (total 3 core)
# makanya di bawah ini nulisnya i=[i] karena num_cpus=1 (cuma pakai 1 core)
actors = [Ocr_pdf.options(num_cpus=1).remote(i=[i]) for i in range(os.cpu_count())]

# worker dikumpulkan jadi satu pool biar gampang proses bagi kerjaan
actor_pool = ActorPool(actors)

# langsung proses kerja
result = list(actor_pool.map(lambda a,v: a.process.remote(v), 
                             [os.path.join(path,file) for path,dirs,files in os.walk('path/to/folder/pdf') for file in files]))
"""

from .parser import Pdf
from .function import Lookup
from .ocr import Ocr_pdf
from .update_typo import update
from .cek import Cek
