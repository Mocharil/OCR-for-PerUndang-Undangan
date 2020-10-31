from .function import Lookup
from .ocr import Ocr_pdf
import pandas as pd
from tika import parser
import re, os, sys, psutil

# tambahan total pasal, ayat, bab, instruksi
# nama file sesuai pdf

class Pdf(object):
    """
    class OCR pdf include extraction with output dictionary generator
    
    """
    def __init__(self, i='default'):
        if sys.platform == 'linux':
            if isinstance(i, int):
                psutil.Process().cpu_affinity([i])
            elif isinstance(i, list) and all([isinstance(x, int) for x in i]):
                psutil.Process().cpu_affinity(i)
                
        self.function = Lookup()
        self.list_ke = self.function.list_ke
        self.PATTERN_PASAL = self.function.PATTERN_PASAL
        self.ocr = Ocr_pdf()
        
    def actual_file(self, filename):  
        filename = filename.replace('PERATURAN DAERAH KABUPATEN2','PERATURAN DAERAH KABUPATEN')
        for pdf in ['.pdf','.PDF','.DOC','.doc','.DOCX','.docx','.HTM','.htm','.odt','.rtf','.ODT']:  
            a = os.path.splitext(filename)[0]+pdf
            if os.path.isfile(a):
                return a
            a = a.replace('/FIX/','/ein/new/')
            if os.path.isfile(a):
                return a          
        return filename
        
    def tentu_pasal(self,x, urut):
        try:
            return int(x)
        except:
            return urut
     
    def get_generator(self,filename):
    
        data,hasil,b,a,p,inst = self.get_data(filename,None,False)
        if hasil!=[]:
            for h in hasil:
                h.update(data)
                h.update({'id':'{}{}'.format(os.path.basename(filename),h.get('id')).replace(' ',''),
                            'total_bab':len(b),'total_pasal':len(p),'total_ayat':a,'total_instruksi':len(inst)})
                yield h 
                
        else:
            yield {'status':'None'}
            
            
    
     
    def get_data(self,filename,savePATH=None, with_ray=True):
        """
        Process extraction pdf PUU

        ...

        Attributes
        ----------
        filename : str
            filename with PDF format
        savePATH : str
            path to save OCR result with txt format
            default : same with path file pdf
            
        with_ray : bool
            if with_ray == False, this function will be generator
            default : False
        
        Methods
        -------
            using regex and flashtext 
        
        Output
        -------
            dictionary generator
        """        
        

        if not savePATH:
            savePATH = os.path.dirname(filename)

        if os.path.splitext(filename)[1]=='.txt':
            try:
                with open(filename) as f:
                    doc = f.read()
            except:
                with open(filename, encoding='latin-1') as f:
                    doc = f.read()
                    

        
        
        elif '.pdf' in os.path.splitext(filename)[1].lower():
            
            doc = self.ocr.process(filename)
            
            if not doc:
                if with_ray:
                    return [{'status':'None'}]
            
                else: 
                    return [],[]
            
            with open(os.path.join(savePATH,
                                   os.path.basename(os.path.splitext(filename)[0]+'.txt')),'w') as f:
                f.write(doc)
                
        else :
            
            doc = parser.from_file(filename)['content']               
                    
        asli = ' '.join(doc.split()).replace(' BAB 11 ',' BAB II ').lower()
        text =  self.function.fixing_text(asli)

        text = re.sub(r'[^0-9a-z!"#$%&\'()*+,-./:;<=>[\\] ]','',text)
        text = re.sub(r'\s+',' ',text)

        text50 = ' '.join(text.split()[:100])   

        nama = re.findall(r'((ketetapan|surat|peraturan|keputusan|instruksi|undang)(.*?)(republik indonesia|nomor|\sno\s))',text50)
        if len(nama)!=0:
            nama = nama[0][0].replace('republik indonesia','').replace('nomor','').strip()
            nama = re.sub(r'\bno\b','',nama).strip()
        else:
            nama = 'None'   

        nama = nama.split('100:')[0].strip()
        nama = nama.split('tanggal')[0].strip()
        nama = nama.replace('\\','').split('nomor')[0].split('no.')[0].split('repub')[0].strip()

                #nomor dan tahun                    
        nomor, tahun = self.function.get_nomor(text, nama)
        nomor = '\n'.join(nomor.split('nomor'))
        nama = nama.replace('!','i').split('repub')[0].strip()
        if nama=='undang':
            nama = 'undang-undang'
        tetap='None'

        #-------- batang tubuh menetapkan -------, jika bernilai None, maka pindah ke folder gagal
        menetapkan, text21= self.function.get_menetapkan(text,nama)  
        if menetapkan=='None':
            if with_ray:
                return [{'status':'None'}]
        
            else: 
                return [],[],0,0,0,0
        RI = r'(?<!'+'\s)(?<!'.join(['berdirinya','\sdi','kejaksaan','anggaran','negara','antara','dan','dari'])+\
                    '\s)'+'republik indonesia\s'+\
                    '(?!dan\s)(?!dengan)(?!dalam\s)(?!untuk\s)(?!nomor)(?!sebagaimana)(?!serikat)(?!yang)(?!tentang)(?!jogjakarta)(?!dahulu)'  
        list_belakang_tentang = ['(?<!wakil\s)(?<!keputusan\s)presiden republik indon',
                        RI,
                         'dengan rahmat .*? esa','menimbang','(?<!peraturan yang menetapkan\s)bahwa','kami, presiden']

        if 'instruksi' in nama:
            belakang = '|'.join(list_belakang_tentang+['dalam rangka','dalam_rangka'])
        else:
            belakang = '|'.join(list_belakang_tentang)
        try:
            tentang = re.findall(nama.split()[0]+r'.*?tentang(.*?)({})'.format(belakang),text)
            if tentang==[]:
                tentang = re.findall(r'tentang(.*?)({})'.format(belakang),text)
            
        except:
            tentang = re.findall(r'tentang(.*?)({})'.format(belakang),text)
        if len(tentang)!=0:
            tentang = tentang[0][0]
            #tentang = tentang.split('.')[0].strip()
        else:
            tentang='None'

   
        tentang = re.split(';\s(?!tambahan)',tentang)[0].strip()
        tentang = tentang.split(' perlu ')[0].split(' bismil')[0].strip()


        #menimbang
        menimbang = self.function.extract(r'imbang(.*?)(?:mengingat|memutuskan|menginstruksikan)',text)
        if menimbang=='None' or len(menimbang)<10:
            a = self.function.extract(r'(bahwa.*?)memutuskan',text)
            menimbang = ' '.join(re.findall(r'(bahwa.*?;)', a))

        #mengingat
        mengingat = self.function.extract(r'ingat(.*?)(?:memutuskan|menginstruksikan)',text).replace(menimbang,'')   
        if mengingat=='None':
            mengingat = self.function.extract(r'ingat(.*?)menginstruksikan',text)
        if mengingat=='None' or mengingat=='':
            mengingat = self.function.extract(r'(bahwa.*?)memutuskan',text).replace(menimbang,'')  

        data = {'file':self.actual_file(filename),'no':nomor,'tahun':tahun,'tentang':tentang,'kind':nama,'menimbang':menimbang,'mengingat':mengingat}

        hasil = []
        number = 0
        umur_status = 'None'
        cabut_status = 'None'
        
        menetapkan = menetapkan.replace(menimbang,'').replace(mengingat,'')
        tt = ' '.join(tentang.split()[-2:])

        menetapkan = menetapkan.replace(tt+',', tt+'.')
        #menentukan pola
        if 'keputusan' in nama or 'instruksi' in nama:
            define = re.findall(r'(\bpertama\b|\bkesatu\b|\bbab\b|\bpasal\b)',menetapkan)
        else:
            define = re.findall(r'(\bbab\b|\bpasal\b)',menetapkan)
              
        if len(define)==0:
            pola  = 'None'
        else:
            pola = define[0]
        #POLA BAB
   
        if pola == 'bab':
            tetap = self.function.extract(r'(.*?) bab \d+ [\w+\s]* pasal \d+',menetapkan)
            pattern_bab = r'(?<!'+'\s)(?<!'.join(['dengan','sesuai','ketentuan',
                    'pelaksanaan','\sdan','yakni','[0-9a-z]\)','[\:]',
                    'antara','berikut','sehingga','satunya','termaksud','dikeluarkan',
                    'menurut','dalam','(?<!huruf)\s[a-z]','(?<!huruf)\s[a-z]\.','dari','terakhir','keseluruhan',
                    'terpilih','atau','demi','pada','maksud' ])+'\s)'+'(?<!-)(?<!")bab (?!ini)([0-9]+)(?!\s*:)'  

            list_bab = re.findall(pattern_bab, menetapkan)

            list_isi_bab = []
            status = False
            for i in re.split(pattern_bab, menetapkan):
                if len(i)<5:
                    status=True
                if status and len(i)>5:
                    list_isi_bab.append(i.strip()) 
                    
            for bab,isi_bab in zip(list_bab,list_isi_bab):           
            
            
                judul_bab = self.function.extract(r'(.*?)pasal', isi_bab)\
                                        .replace('presiden republik indonesia','').replace('bab {}'.format(bab),'').strip()
                #isi_bab = isi_bab.replace(judul_bab,'')
                judul_bab = judul_bab.split(' bagian ')[0].strip()
                judul_bab = judul_bab.split(' paragraf ')[0].strip()
                judul_bab = re.sub(r'([a-zA-Z]:\\[^/:\*\?<>\|]+\.\w{2,6})|(\\{2}[^/:\*\?<>\|]+\.\w{2,6})','',judul_bab)
                judul_bab = judul_bab.replace('.','').strip()
                
                
                #ambil list pasal
                status = False
                list_isi_pasal = []

                for i in re.split(self.PATTERN_PASAL,isi_bab):
                    if len(i)<5:
                        status=True
                    if status and len(i)>5:
                        list_isi_pasal.append(i.strip())
                #apakah ada pasal?
                if len(list_isi_pasal)!=0:
                    for pasal, isi_pasal in zip(self.function.get_pasal(isi_bab),
                                                list_isi_pasal):
                        #apakah ada ayat?
                        if re.search(r'(?<!ayat\s)\((\d+)\)',' '.join(isi_pasal.split()[:1])):
                            result = [ii for ii in re.split(r'(?<!ayat\s)\((\d+)\)', isi_pasal) if len(ii)>2]
                            for index, ayat in enumerate(result, start=1):   
                                number+=1
                                hasil.append({'bab':bab,'judul_bab':judul_bab,
                                              'pasal':pasal,'ayat':str(index),'isi':ayat,'id':number})

                            if 'penutup' in judul_bab:
                                if umur_status =='None':
                                    umur_status = self.function.umur(ayat)
                                if cabut_status == 'None':
                                    cabut_status = self.function.cabut(ayat)
                        else:
                            number+=1
                            hasil.append({'bab':bab,'judul_bab':judul_bab,
                                              'pasal':pasal,'isi':isi_pasal,'id':number})
                            if 'penutup' in judul_bab:
                                if umur_status =='None':
                                    umur_status = self.function.umur(isi_pasal)
                                if cabut_status == 'None':
                                    cabut_status = self.function.cabut(isi_pasal)

                else:
                    #jika tidak ada pasal
                    number+=1
                    hasil.append({'bab':bab,'judul_bab':judul_bab,'isi':isi_bab,'id':number})
                    if 'penutup' in judul_bab:
                        if umur_status =='None':
                            umur_status = self.function.umur(isi_bab)
                        if cabut_status == 'None':
                            cabut_status = self.function.cabut(isi_bab)  

        #POLA PASAL ROMAWI AND INT   
        elif pola=='pasal':
            tetap = self.function.extract(r'(.*?)pasal [0-9a-z]+', menetapkan)        
            isi_bab = menetapkan
            menetapkan_roman, _ = self.function.get_menetapkan(self.function.fixing_text_roman(asli.replace('republik indonesia','')),nama)
            pasal_asli = self.function.get_pasal(menetapkan_roman)
            
            status_pasal = True
            
            if 'ubah' in tentang or 'i' in pasal_asli: 
                
                try:
                    list_pasal = []
                    
                    for i in self.function.get_pasal(menetapkan_roman.replace('pasal 1 ','pasal i ')):
                        try:
                          
                            self.function.roman_to_int(i)
                            list_pasal.append(i)     
                           
                                
                        except:
                            pass

                    for ix, pasal in enumerate(list_pasal):
                        try:
                            isis = re.findall(r'pasal {} (.*?)pasal {}\.?'.format(pasal, list_pasal[ix+1]), menetapkan_roman)[0]
                        except:
                            isis = re.findall(r'pasal {} (.*)'.format(pasal),menetapkan_roman)[0]
                        number+=1

                        hasil.append({'pasal':str(ix+1),'isi':isis,'id':number})  
                        if umur_status =='None':
                            umur_status = self.function.umur(isis)
                        if cabut_status == 'None':
                            cabut_status = self.function.cabut(isis) 
                    if len(hasil)==0:
                        ggg #make error
                except:
                    hasil = []
                    status = False
                    list_isi_pasal = []
                    for i in re.split(self.PATTERN_PASAL,menetapkan):
                        if len(i)<5:
                            status=True
                        if status and len(i)>5:
                            list_isi_pasal.append(i.strip())


                    for pasal, isi_pasal in zip(self.function.get_pasal(menetapkan),list_isi_pasal):
                        if re.search(r'(?<!ayat\s)\((\d+)\)',' '.join(isi_pasal.split()[:1])):
                            result = [ii for ii in re.split(r'(?<!ayat\s)\((\d+)\)', isi_pasal) if len(ii)>2]
                            for index, ayat in enumerate(result, start=1):   
                                number+=1
                                hasil.append({'pasal':pasal,'ayat':str(index),'isi':ayat,'id':number})  
                                if umur_status =='None':
                                    umur_status = self.function.umur(ayat)
                                if cabut_status == 'None':
                                    cabut_status = self.function.cabut(ayat)  
                        else:
                            number+=1
                            hasil.append({'pasal':pasal,'isi':isi_pasal,'id':number})
                            if umur_status =='None':
                                umur_status = self.function.umur(isi_pasal)
                            if cabut_status == 'None':
                                cabut_status = self.function.cabut(isi_pasal) 


            else:
                status = False
                list_isi_pasal = []
                for i in re.split(self.PATTERN_PASAL,menetapkan):
                    if len(i)<3:
                        status=True
                    if status and len(i)>3:
                        list_isi_pasal.append(i.strip())


                for pasal, isi_pasal in zip(self.function.get_pasal(menetapkan),list_isi_pasal):
                    if re.search(r'(?<!ayat\s)\((\d+)\)',' '.join(isi_pasal.split()[:1])):
                        result = [ii for ii in re.split(r'(?<!ayat\s)\((\d+)\)', isi_pasal) if len(ii)>2]
                        for index, ayat in enumerate(result, start=1):   
                            number+=1
                            hasil.append({'pasal':pasal,'ayat':str(index),'isi':ayat,'id':number})  
                            if umur_status =='None':
                                umur_status = self.function.umur(ayat)
                            if cabut_status == 'None':
                                cabut_status = self.function.cabut(ayat)  
                    else:
                        number+=1
                        hasil.append({'pasal':pasal,'isi':isi_pasal,'id':number})
                        if umur_status =='None':
                            umur_status = self.function.umur(isi_pasal)
                        if cabut_status == 'None':
                            cabut_status = self.function.cabut(isi_pasal) 


        #POLA INSTRUKSI
        
        elif pola =='pertama':  
            tetap = self.function.extract(r'(.*?)pertama', menetapkan)
            for i,ke in enumerate(self.list_ke):
                result = self.function.extract(r'{}(.*?){}'.format(ke, self.list_ke[i+1]), menetapkan)
                if result=='None':
                    result = self.function.extract(r'{}(.*)'.format(ke), menetapkan)
                    number+=1
                    hasil.append({'instruksi':ke,'isi':result,'id':number}) 
                    break
                number+=1
                hasil.append({ 'instruksi':ke,'isi':result,'id':number})  

        elif pola=='kesatu':
            tetap = self.function.extract(r'(.*?)kesatu', menetapkan)
            for i,ke in enumerate(self.list_ke):
                if ke=='pertama':
                    result = self.function.extract(r'{}(.*?){}'.format('kesatu', self.list_ke[i+1]), menetapkan)
                else:
                    result = self.function.extract(r'{}(.*?){}'.format(ke, self.list_ke[i+1]), menetapkan)
                if result=='None':
                    result = self.function.extract(r'{}(.*)'.format(ke), menetapkan)
                    number+=1
                    hasil.append({'instruksi':ke,'isi':result,'id':number}) 
                    break
                number+=1
                hasil.append({'instruksi':ke,'isi':result,'id':number})        

        if menetapkan!='None' and hasil==[]:
            number+=1
            hasil.append({'isi':menetapkan,'id':number})

        # ---------- tanggal ttd ----------
        #text = text.replace(menimbang,'').replace(mengingat,'').replace(menetapkan,'')
        ditetapkan = 'None'
        diundangkan = 'None'

        ditetapkan,diundangkan = self.function.tanggal_mode(text21)
        if ditetapkan =='None':
            tgl = self.function.tanggal_mode1(text21)
            if tgl[0]!='None':
                ditetapkan = tgl[0]
                try:
                    diundangkan = tgl[1]
                except:
                    pass
            else:
                tgl = self.function.tanggal_mode2(text21)
                df = pd.DataFrame(tgl)
                dx = df.dropna()
                if dx.shape[0]==0:
                    tgl = df['result'].tolist()
                    ditetapkan = tgl[0]
                    try:
                        diundangkan = tgl[1]
                    except:
                        pass          
                else:
                    tgl = dx['result'].tolist()        
                    ditetapkan = tgl[0]
                    try:
                        diundangkan = tgl[1]
                    except:
                        pass   

        data.update({'menetapkan':tetap,'ditetapkan':ditetapkan,'diundangkan':diundangkan})

        terkait, pemrakarsa = self.function.potong_mengingat(mengingat)
        if terkait ==[]:
            terkait = self.function.ter(mengingat)
        terkait.sort(key=lambda s: self.function.sort_tahun(s), reverse=True)
        terkait.sort(key=lambda s: self.function.sort_terkait(s))
        data.update({'terkait':terkait,'pemrakarsa':pemrakarsa,'umur':umur_status,'dicabut/mencabut':cabut_status})

        ##==================================PENJELASAN=======================================
        
        
        text_origin = re.sub(r'\s+',' ',doc)    
        
        text_origin = re.sub(r'[^\x00-\x7F]','-',text_origin).replace('|','') 
        text_origin = re.sub(r'-{2,}','-',text_origin)        
        a = re.findall('\d+\s?/\s?\d+',text_origin)
        if len(a)>=2 and len(a)==int(a[0].split('/')[-1]) and len(set([i.split('/')[-1] for i in a]))==1:
            text_origin = re.sub('\d+\s?/\s?\d+',' ',text_origin)           
        # umum = re.findall('I\.\s?UMUM(.*?)II.\s?PASAL', text_origin.replace('\n',''))
        umum = re.findall('\sI\.\s*(?:Penjelasan|PENJELASAN)?\s*(?:Umum|UMUM)(.*?)II.\s*PASAL', text_origin)
        if umum!=[]:
            umum = umum[0].strip()
            demi_pasal  = isi_bab = re.findall(r'PASAL DEMI PASAL(.*?)TAMBAHAN LEMBARAN', text_origin.replace('\n',''))
            if demi_pasal ==[]:
                demi_pasal  = isi_bab = re.findall(r'PASAL DEMI PASAL(.*)', text_origin.replace('\n',''))
            if demi_pasal!=[]:
                demi_pasal = demi_pasal[0].strip()
            else:
                demi_pasal = 'None'
        else:
            umum = 'None'
            demi_pasal = 'None'

        b,a,p,inst = (set(),0,set(),set())
        for i in hasil:
            if i.get('ayat'):
                a+=1
            if i.get('bab'):
                b.update([i.get('bab')])
            if i.get('pasal'):
                p.update([i.get('pasal')]) 
            if i.get('instruksi'):
                inst.update([i.get('instruksi')]) 
        total_pasal=0    
        if len(p)!=0 :
            p1 = len(p)
            p2 = max([self.tentu_pasal(i,urut) for urut,i in enumerate(p, start=1)])              
            total_pasal = p1 if p1>p2 else p2
        total_bab=0    
        if len(b)!=0 :    
            b1 = len(b)
            b2 = max([self.tentu_pasal(i,urut) for urut,i in enumerate(b, start=1)])              
            total_bab = b1 if b1>b2 else b2               
      
        if with_ray:
            result = []
            for h in hasil:
                h.update(data)
                isi = h.get('isi')
                isi = re.split(r'\sbagian (?:ke|perta)[a-z]+',isi)[0]
      
                h.update({'isi':isi.strip(),'id':'{}{}{}'.format(os.path.basename(filename),nomor,h.get('id')).replace(' ',''),
                            'total_bab':total_bab,'total_pasal':total_pasal,'total_ayat':a,'total_instruksi':len(inst),
                            'number':h.get('id')})
                            
                if umum!='None':
                    h.update({'umum':umum,'pasal_demi_pasal':demi_pasal})
                   
              
                
                result.append(h)
                
            
            return self.function.rombak_ketentuan_umum(result)            
            
        return data,hasil,b,a,p,inst 


