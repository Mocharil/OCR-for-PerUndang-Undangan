from tika import parser
import ocrmypdf
import warnings
warnings.filterwarnings("ignore")
from tqdm import tqdm
import pytesseract, os,sys, psutil
os.environ['TIKA_SERVER_JAR'] = 'https://repo1.maven.org/maven2/org/apache/tika/tika-server/1.19/tika-server-1.19.jar'
import pillowfight
from PIL import Image 
Image.MAX_IMAGE_PIXELS = 1000000000 
import cv2
import numpy as np 
from PyPDF2 import PdfFileWriter, PdfFileReader
from pdf2image import convert_from_path
import numpy as np
import math
import fitz
from scipy import ndimage

class Ocr_pdf(object):
    """
    class for ocr pdf to text
    
    """
    def __init__(self, i='default'):
        if sys.platform == 'linux':
            if isinstance(i, int):
                psutil.Process().cpu_affinity([i])
            elif isinstance(i, list) and all([isinstance(x, int) for x in i]):
                psutil.Process().cpu_affinity(i)
                
                
    def get_string_from_pdf(self,file_pdf):
        file_txt = os.path.splitext(file_pdf)[0]+'.txt'
        ocrmypdf.ocr(input_file  = file_pdf,
                     output_file = os.path.splitext(file_pdf)[0]+'_ocr.pdf',
                     sidecar = file_txt,
                     oversample=350, deskew=True,clean_final=True,
                     tesseract_pagesegmode=1, tesseract_oem=1, 
                     language=["ind","eng"],progress_bar=False, force_ocr=True)
     
        with open(file_txt) as f:
            text = f.read()
        os.remove(file_txt)
        os.remove(os.path.splitext(file_pdf)[0]+'_ocr.pdf')
        return text                
                                

    def check_pdf_scanned(self,file_name):
        # This algorithm calculates the percentage of document that is covered by (searchable) text
        
        page_num = 0
        text_perc = 0.0

        doc = fitz.open(file_name)

        for page in doc:
            page_num = page_num + 1

            page_area = abs(page.rect)
            text_area = 0.0
            for b in page.getTextBlocks():
                r = fitz.Rect(b[:4]) # rectangle where block text appears
                text_area = text_area + abs(r)
            text_perc = text_perc + (text_area / page_area)

        text_perc = text_perc / page_num

        # If the percentage of text is very low, the document is most likely a scanned PDF
        if text_perc < 0.01:
            return True
        return False
            
 
    def clean_noise(self,img):
        """
        image processing for denoising image using cv2

        ...

        Attributes
        ----------
        img : Image
        
       
        """ 
        dst = cv2.fastNlMeansDenoisingColored(img,None,10,10,7,21)        
        return dst 

    def apply_unpaper(self,img):
        """
        image processing using unpaper algorithm

        ...

        Attributes
        ----------
        img : Image
       
        """ 
        #change format array to PIL Image format
        in_img = Image.fromarray(img)
        out_img = pillowfight.ace(in_img, seed=12345)
        #out_img = pillowfight.ace(in_img)
        # unpaper order
        #out_img = pillowfight.unpaper_blackfilter(out_img)
        out_img = pillowfight.unpaper_noisefilter(out_img)
        out_img = pillowfight.unpaper_blurfilter(out_img)
        out_img = pillowfight.unpaper_masks(out_img)
        out_img = pillowfight.unpaper_grayfilter(out_img)
        out_img = pillowfight.unpaper_border(out_img)   

        #change to array format
        output = np.array(out_img) 
        # Convert RGB to BGR 
        output = output[:, :, ::-1].copy() 

        return output

    def fix_rotate(self,img):
        """
        rotate image

        ...

        Attributes
        ----------
        img : Image

        """      
        img_edges = cv2.Canny(img, 150, 150, apertureSize=3)
        img_line = img.copy()
        lines = cv2.HoughLinesP(img_edges, 1, math.pi / 180.0, 100, minLineLength=100, maxLineGap=5)
        angles = []
        median_angle = 0
        if lines!=[]:
            for x1, y1, x2, y2 in lines[0]:
                cv2.line(img_line, (x1, y1), (x2, y2), (255, 0, 0), 3)
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                angles.append(angle)

            median_angle = np.median(angles)    
        return median_angle

    #================image to text==============
    def get_string(self,fileJPG):
        """
        convert image to text include image processing
        ...

        Attributes
        ----------
        fileJPG : str
            type file Image (png, jpg,jpeg)
        
        Methods
        -------
        using pytesseract
        """       
        image = cv2.imread(fileJPG)
        image_origin = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        angle = self.fix_rotate(image_origin)

        image_rotate = ndimage.rotate(image_origin, angle) #change rotate
        image_unpaper = self.apply_unpaper(image_rotate)
        image_denoise = self.clean_noise(image_unpaper)  
        
        #-- psm 6 Assume a single uniform block of text
        #-- oem 1 LSTM
        #- l ind+eng (indonesia and english)
        #-- dpi 400 best result
        config='--dpi 350 -l ind+eng --oem 1 --psm 6'
        text = pytesseract.image_to_string(image_denoise, config = config)

        return text

    def read1(self,filename):
        """
        Process with the first methods

        ...

        Attributes
        ----------
        filename : str
            filename with PDF format
        
        Methods
        -------
        split pdf per page, define it as text or image, then convert to text
        """    
    
        src_path = os.path.dirname(filename)
        name = os.path.basename(filename)
        name_img = name.replace(os.path.splitext(name)[-1],'.jpg')
        result='' 
        inputpdf = PdfFileReader(open(filename, "rb"), strict = False)
        print('split doc', end='\r')

        numpages = inputpdf.numPages

        for i in range(numpages):
            output = PdfFileWriter()
            output.addPage(inputpdf.getPage(i))
            with open(os.path.join(src_path,"page{}{}".format(i,name)), "wb",buffering=0) as outputStream:
                output.write(outputStream)
        print('ocr',end = '\r')
        for i in range(numpages):
            file = os.path.join(src_path,"page{}{}".format(i,name))
            #jika tidak di scanned
            if not self.check_pdf_scanned(file):       
                doc = parser.from_file(file)['content']
                result+=doc
                print('text-{}'.format(i),end='\r')

            else:
                pages = convert_from_path(file, 450)
                
                
                file = os.path.join(src_path,"page{}{}".format(i,name_img))
                for page in pages:
                    page.save(file, 'JPEG')
                print('image-{}'.format(i), end='\r')
                result+= self.get_string(file) 

        for i in range (numpages):
            try:
                os.remove(os.path.join(src_path,"page{}{}".format(i,name)))
                os.remove(os.path.join(src_path,"page{}{}".format(i,name_img)))
            except OSError as e:
                pass

        return result

    def read2(self,filename):
    
        """
        Process with the second methods

        ...

        Attributes
        ----------
        filename : str
            filename with PDF format
        
        Methods
        -------
            read pdf as text, if return None, convert all page into image
        """
        name = os.path.basename(filename)
        name_img = name.replace(os.path.splitext(name)[-1],'.jpg')
                          
        src_path = os.path.dirname(filename)
        if not self.check_pdf_scanned(filename): 
            doc = parser.from_file(filename)['content']
            return doc

        result = ''
        pages = convert_from_path(filename, 450)
        for i, page in enumerate(pages):
            file = os.path.join(src_path,"page{}{}".format(i,name_img))   
            page.save(file, 'JPEG')
            print('image-{}'.format(i), end='\r')
            result+= self.get_string(file)
            os.remove(file)

        return result

    def read_new(self,filename):
        src_path = os.path.dirname(filename)
        name = os.path.basename(filename)
        result='' 
        inputpdf = PdfFileReader(open(filename, "rb"), strict = False)
        print('split doc', end='\r')

        numpages = inputpdf.numPages

        for i in tqdm(range(numpages)):
            output = PdfFileWriter()
            output.addPage(inputpdf.getPage(i))
            file_split = os.path.join(src_path,"page{}{}".format(i,name))
            with open(file_split, "wb",buffering=0) as outputStream:
                output.write(outputStream)

            #jika tidak di scanned 
            if not self.check_pdf_scanned(file_split):
                doc = parser.from_file(file_split)['content']
                result+=doc
                print('text-{}'.format(i),end='\r')

            else:
                result+= self.get_string_from_pdf(file_split)  
                
            os.remove(file_split)

        return result


    def delete(self,filename):
        name = os.path.basename(filename)
        clear_name = os.path.splitext(name)[0]
        dir_name = os.path.dirname(filename)
        for file in os.listdir(dir_name):
            if 'page' in file and clear_name in file:
                os.remove(os.path.join(dir_name,file))

    def process(self,filename):
        """
        Process OCR file pdf with 3 methods

        ...

        Attributes
        ----------
        filename : str
            filename with PDF format
        
        Methods
        -------
            split pdf per page
        """
    
        for func in [self.read_new, self.read1,self.read2]:
            try:
                return func(filename)
            except Exception as e:
                print(e)
                self.delete(filename)
                pass
                
                
    def to_text(self,filename, savePATH = None):
        result = self.process(filename)
        if result:
            
            if not savePATH:
                savePATH = os.path.dirname(filename)
            
            name = os.path.basename(filename)
            name = os.path.splitext(name)[0]+'.txt'
            
            
            fileSAVE = os.path.join(savePATH,name)
            with open(fileSAVE,'w') as f:
                f.write(result)


                
        