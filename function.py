import json, os,re, string, shutil , sys, psutil
from collections import OrderedDict, Counter
from tqdm import tqdm
from flashtext import KeywordProcessor
import pandas as pd
import aril2
class Lookup(object):
    """
    class all function for extraction data pdf
    
    """
    def __init__(self, i='default'):
        if sys.platform == 'linux':
            if isinstance(i, int):
                psutil.Process().cpu_affinity([i])
            elif isinstance(i, list) and all([isinstance(x, int) for x in i]):
                psutil.Process().cpu_affinity(i)
        
        with open(os.path.join(aril2.__dirname__,'tools','list_ke.json')) as f:
            self.list_ke = json.load(f)
        with open(os.path.join(aril2.__dirname__,'tools','list_flashtext.json')) as f:
            self.typo_flash = json.load(f)
        print('ocr pdf for rpuu')
        
        self.keyword_processor = KeywordProcessor()
        self.keyword_processor.add_keywords_from_dict(self.typo_flash)  
        
        self.bulan = ['November', 'October', 'June', 'April', 'December', 'August', 'May', 'January', 'Sep',
                     'Agustus', 'Oct', 'Oktober', 'July', 'March', 'Jan', 'Juni', 'Dec',
                     'Apr', 'Jul', 'Februari', 'Nov', 'September', 'Aug', 'Nopember', 'Feb',
                     'Januari', 'Maret', 'Desember', 'Mei', 'Mar', 'Jun', 'Juli', 'February']
        self.list_satu = ['memutuskan','menetapkan','agar','setiap','orang','supaya','yang','maha',
                                     'ditetapkan','disahkan','mulai','diundangkan','djakarta','berlaku',
                                     'instruksi','dikeluarkan','republik','indonesia','dengan','ketetapan',
                                     'tentang','tetapkan','presiden','peraturan','esa','nomor',
                                     'menimbang','tahun','men1mbang','dengan','rahmat','tuhan','pemerintah',
                                     'undang-undang','menteri','keputusan','instruksi', 'perundang-undangan',
                          'menginstruksikan','bab','pasal','daerah','kota','walikota','dewan','gubernur','bupati','qanun']
        
        self.label = [i.lower() for i in self.bulan]+['tahun']
        self.WORDS = Counter(self.label)
        

        self.PATTERN_PASAL = r'(?<!'+'\s)(?<!'.join(['(?<!pasal)(?<!menjadi)(?<!ayat)\s[0-9]{3}\.','(?<!pasal)(?<!menjadi)(?<!ayat)\s[0-9]{2}\.',
            '(?<!pasal)(?<!menjadi)(?<!ayat)\s[0-9]\.','dengan','ketentuan',
            '\sdan','yakni','[0-9a-z]\)','(?<!,)-','[\,\:]','juga','sesuai','mengenai','ataupun','seluruh','berdasarkan','juncto','b\. pajak penghasilan',
            'antara','berikut','sehingga','satunya','adalah','dikeluarkan',' dad','menambah','memuat','sepanjang','serta',
            'menurut','dalam','\s[a-z]','(?<!huruf)\s[a-z]\.','dari','terakhir','keseluruhan','kunya','menjadi','beberapa','memperhatikan',
            'terpilih','atau','demi','pada','maksud','kecuali','terutama','menambah','mengubah','disebut','perubahan','dihapuskannya',
            'indonesia'])+'\s)'+'(?<!-)(?<!")(?<!\()pasal (?!ini)([0-9]+[a-z]*|penutup|ix|x?iv|v|x?v?i{1,3})(?:$|\s|\.)(?!ayat)(?!\(baru\))(?!dan)(?!menjadi)(?!huruf)'       
        
    def P(self, word): 
        "Probability of `word`."
        return self.WORDS[word] / sum(self.WORDS.values())

    def correction(self,word): 
        """
        correct incorrect spelling 

        ...

        Attributes
        ----------
        word : str
            filename with PDF format
        
        Methods
        -------
            Levenshtein Distance

        """     
        return max(self.candidates(word), key=self.P)

    def candidates(self,word): 
        "Generate possible spelling corrections for word."
        return (self.known([word]) or self.known(self.edits1(word)) or self.known(self.edits2(word)) or [word])

    def known(self,words): 
        "The subset of `words` that appear in the dictionary of WORDS."
        return set(w for w in words if w in self.WORDS)

    def edits1(self,word):
        "All edits that are one edit away from `word`."
        letters    = 'abcdefghijklmnopqrstuvwxyz'
        splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
        deletes    = [L + R[1:]               for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
        replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
        inserts    = [L + c + R               for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def edits2(self,word): 
        "All edits that are two edits away from `word`."
        return (e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))
    
    def fixing_text(self,text):       
        b = self.keyword_processor.replace_keywords(str(text)) 
        
        a = re.findall('\d+\s?/\s?\d+',b)
        if len(a)>=2 and len(a)==int(a[0].split('/')[-1]) and len(set([i.split('/')[-1] for i in a]))==1:
            b = re.sub('\d+\s?/\s?\d+',' ',b)        
            
        b = b.replace('pasal | ','pasal i ').replace('pasal il ',' ii ')
        
        #path file
        #b = re.sub(r'([a-zA-Z]:\\[^/:\*\?<>\|]+\.\w{2,6})|(\\{2}[^/:\*\?<>\|]+\.\w{2,6})','',b)   
        #link
        b = re.sub(r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)','',b)
        b = re.sub(r'(www\.)[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)','',b)
        b = re.sub(r'\spal\s(\d+)',r' pasal \1',b)
        b = re.sub('\sno\.',' nomor',b)
        b = re.sub(r'[^\x00-\x7F]','-',b)
        b = re.sub(r'-{2,}','-',b)
        b = b.replace('undang undang','undang-undang')
        b = b.replace('_','').replace('-:',':').replace('|','')
        b = re.sub('(pasa1)(\d+)',r'pasal \2',b)
        b = re.sub(r'\ssk no \d{3,} a\s',' ',b)
        b = re.sub('(bab)(\d+)',r'bab \2',b)
        b = re.sub(r'([0-9]{4})\.',r'\1',b).replace('pasall','pasal 1')
        b = b.replace('=ndonesia','indonesia')
        b = b.replace('pega\\iiai','pegawai').replace('i(','k').replace('1{','k')
        b = b.replace("\'1\'arif",'tarif').replace('undang.undai\\g','undang-undang')
        b = re.sub(r'-\s?[0-9]+\s?-','',b).replace('i-i','h').replace("'",'')
        b = re.sub(r'-\s(.*?)',r'-\1',b)  
        b = re.sub(r'[a-z0-9]+\s?\.\s?\.\s?\.\s?(presiden republik indonesia)?','',b)
        b = re.sub('|','',b)
        b = re.sub(r"'''",'',b).replace('(21 ','(2) ')
        b = b.replace('repu\'blik','republik')
        b = re.sub(r'https?://[a-z0-9\.]+|[a-z0-9\.]+\.go\.id|[a-z0-9\.]+\.co\.id','',b)
        b = re.sub(r'\b([a-z0-9\.]+)\s+\1\b',r'\1',b)
        b = re.sub(r'([a-z\.0-9]\.)\s+\1',r'\1',b)
        b = re.sub(r'(\([0-9a-z]+\))\s+\1',r'\1',b).replace('presid\'en','presiden')
        b = re.sub(r'\s+',' ',b).strip()
        b = re.sub(r'(\d+)1ahun(\d{4})',r'\1 tahun \2',b)
        b = b.replace('/pusatdata ',' ').replace('www.hukumonline.com','')
        
        text = re.sub(r'\bditetapka.\b','ditetapkan ',b)
        text = re.sub(r'-\s?[0-9]\s?-','',text)
        text = re.sub(r'\s+',' ',text)
        text = re.sub(r'memutusi\s?\(\s?an','memutuskan',text)
            
        for v in list(string.ascii_lowercase):
            if v=='i':
                text = re.sub(r'(?<!bab\s)(?<!pasal\s)(?<!bagian\s)(?<![vx]){}{{4,}}'.format(v),v,text)
            else:
                text = re.sub(r'(?<!bab\s)(?<!pasal\s)(?<!bagian\s)(?<![vx]){}{{3,}}'.format(v),v,text)

        text = re.sub(r't+e+t+a+p+k+a+n+','tetapkan',text)
        for t in self.list_satu:
            a = '\s*?'.join(list(t))
            text = re.sub(r'{}'.format(a),t,text)
        for i in range(70):
            #text = re.sub(r'\b{}\b'.format(self.int_to_roman(i+1).lower()),str(i+1),text)
            text = re.sub(r'(bab|pasal)\s\b{}\b'.format(self.int_to_roman(i+1).lower()),r'\1 '+str(i+1),text)  
            
        text = re.sub(r't+e+t+a+p+k+a+n+','tetapkan',text)
        for t in self.list_ke:
            a = '\s*?'.join(list(t))
            text = re.sub(r'{}'.format(a),t,text)
        text = re.sub(r'pasal([0-9]+)',r'pasal \1', text).replace('d11etapkan','ditetapkan')


        #for i in re.findall(r'tahun ([olszti0-9]{4})',b):
         #   b = b.replace(i,i.replace('o','0').replace('i','1').replace('l','1').replace('s','5').replace('z','2').replace('t','1'))
        #for i in re.findall(r'nomor\s?\:?\s?([oltszi0-9]{2,4})',b):
         #   b = b.replace(i,i.replace('o','0').replace('i','1').replace('l','1').replace('s','5').replace('z','2').replace('t','1'))

        #text = self.keyword_processor.replace_keywords(text) 
        text = re.sub(r'(?<![a-z0-9()])di\)','(2)',text).replace('lembaran republik indonesia','lembaran ri') 

        text = re.sub(' https?:/*.*?\s',' ',text)
        return text    

    def fixing_text_roman(self,text):
        b = self.keyword_processor.replace_keywords(str(text))
        b = b.replace('pasal | ','pasal i ').replace('pasal il ',' ii ')
       # b = re.sub(r'([a-zA-Z]:\\[^/:\*\?<>\|]+\.\w{2,6})|(\\{2}[^/:\*\?<>\|]+\.\w{2,6})','',b)
        b = re.sub(r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)','',b)
        b = re.sub(r'(www\.)[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)','',b)
        b = re.sub(r'[^\x00-\x7F]','-',b).replace('|','') 
        b = re.sub(r'-{2,}','-',b)
        b = re.sub('\sno\.',' nomor',b)
        b = b.replace('undang undang','undang-undang').replace('_','').replace('-:',':')
        b = re.sub(r'\spal\s(\d+)',r' pasal \1',b)
        b = re.sub('(pasa1)(\d+)',r'pasal \2',b).replace('kesatu','pertama')
        b = re.sub('(bab)(\d+)',r'bab \2',b).replace(' di) ',' (2) ')
        b = re.sub(r'([0-9]{4})\.',r'\1',b)
        b = re.sub('|','',b)
        b = b.replace('pega\\iiai','pegawai').replace('i(','k')
        b = b.replace("\'1\'arif",'tarif').replace('undang.undai\\g','undang-undang')
        b = re.sub(r'-\s?[0-9]+\s?-','',b).replace('i-i','h').replace("'",'')
        b = re.sub(r'-\s(.*?)',r'-\1',b)  
        b = re.sub(r'[a-z0-9]+\s?\.\s?\.\s?\.\s?(presiden republik indonesia)?','',b)
        b = re.sub(r"'''",'',b).replace('(21 ','(2) ')
        b = b.replace('=ndonesia','indonesia')
        b = b.replace('repu\'blik','republik')
        b = re.sub(r'https?://[a-z0-9\.]+|[a-z0-9\.]+\.go\.id|[a-z0-9\.]+\.co\.id','',b)
        b = re.sub(r'\b([a-z0-9\.]+)\s+\1\b',r'\1',b)
        b = re.sub(r'([a-z\.0-9]\.)\s+\1',r'\1',b)
        b = re.sub(r'(\([0-9a-z]+\))\s+\1',r'\1',b).replace('presid\'en','presiden')
        b = re.sub(r'\s+',' ',b).strip() 
        b = re.sub(r'(\d+)1ahun(\d{4})',r'\1 tahun \2',b)
        b = b.replace('/pusatdata ',' ').replace('www.hukumonline.com','')
        #for i in re.findall(r'tahun ([olszti0-9]{4})',b):
         #   b = b.replace(i,i.replace('o','0').replace('i','1').replace('l','1').replace('s','5').replace('z','2').replace('t','1'))
        #for i in re.findall(r'nomor\s?\:?\s?([oltszi0-9]{2,4})',b):
         #   b = b.replace(i,i.replace('o','0').replace('i','1').replace('l','1').replace('s','5').replace('z','2').replace('t','1'))


        text = re.sub(r'\bditetapka.\b','ditetapkan ',b)
        text = re.sub(r'-\s?[0-9]\s?-','',text)
        text = re.sub(r'\s+',' ',text)
        text = re.sub(r'memutusi\s?\(\s?an','memutuskan',text)

        text = re.sub(r't+e+t+a+p+k+a+n+','tetapkan',text)
        for t in self.list_satu:
            a = '\s*?'.join(list(t))
            text = re.sub(r'{}'.format(a),t,text)
        text = re.sub(r't+e+t+a+p+k+a+n+','tetapkan',text)
        for t in self.list_ke:
            a = '\s*?'.join(list(t))
            text = re.sub(r'{}'.format(a),t,text)
        text = re.sub(r'pasal([0-9]+)',r'pasal \1', text).replace('d11etapkan','ditetapkan')
        #text = self.keyword_processor.replace_keywords(text)
        text = re.sub(r'(?<![a-z0-9()])di\)','(2)',text).replace('lembaran republik indonesia','lembaran ri')    
        text = re.sub(' https?:/*.*?\s',' ',text)        
        return text    

    def int_to_roman(self,input):
        """ Convert an integer to a Roman numeral. """

        if not isinstance(input, type(1)):
            raise (TypeError, "expected integer, got %s" % type(input))
        if not 0 < input < 4000:
            raise (ValueError, "Argument must be between 1 and 3999")
        ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
        nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
        result = []
        for i in range(len(ints)):
            count = int(input / ints[i])
            result.append(nums[i] * count)
            input -= ints[i] * count
        return ''.join(result)

    def roman_to_int(self,input):
        """ Convert a Roman numeral to an integer. """

        if not isinstance(input, type("")):
            raise (TypeError, "expected string, got %s" % type(input))
        input = input.upper(  )
        nums = {'M':1000, 'D':500, 'C':100, 'L':50, 'X':10, 'V':5, 'I':1}
        sum = 0
        for i in range(len(input)):
            try:
                value = nums[input[i]]
                # If the next place holds a larger number, this value is negative
                if i+1 < len(input) and nums[input[i+1]] > value:
                    sum -= value
                else: sum += value
            except KeyError:
                raise (ValueError, 'input is not a valid Roman numeral: %s' % input)
        # easiest test for validity...
        if self.int_to_roman(sum) == input:
            return sum
        else:
            raise (ValueError, 'input is not a valid Roman numeral: %s' % input)

            
    def sort_terkait(self,puu):
        for index, i in enumerate(['1945','(?<!pengganti\s)undang-undang','peraturan.*?undang',
                            'peraturan pemerintah','peraturan presiden','keputusan presiden',
                                   'instruksi presiden','peraturan menteri','keputusan menteri',
                                   'peraturan daerah provinsi','peraturan gubernur','peraturan daerah',
                                   'peraturan bupati']):
            if re.search(r'{}'.format(i),puu):
                return index
        return 20

    def sort_tahun(self,puu):
        try:
            return int(re.findall('\d{4}',puu)[0])
        except:
            return 0
        
        
    def atoi(self,text):
        return int(text) if text.isdigit() else text
    def natural_keys(self,text):
        return [self.atoi(c) for c in re.split(r'(\d+)', text)]
    def extract(self,pattern, text):
        try:
            return re.findall(pattern, text)[0].strip()
        except:
            return 'None'

    def get_nomor(self,text,nama):

        text50  = ' '.join(text.split()[:100]).replace(' no ',' nomor ').replace(' no. ',' nomor ')
        nama = nama.replace('(','\(').replace(')','\)')
        try:
            pattern = nama+'.*?(?<!eko)no\.?m?o?r?\s?\:?(.*?)(tahun|tentang)'
            nomor = re.findall(r'{}'.format(pattern),text50)
        except:
            nomor = re.findall('no\.?m?o?r?\s?\:?(.*?)(tahun|tentang)',text50)

        if len(nomor)!=0:
            ket = nomor[0][1].strip()
            nomor = nomor[0][0].split('tentang')[0].split('tanggal')[0].replace(' ','')
            if ket=='tentang': 
                tahun = nomor[-4:]
                try:
                    if int(tahun) not in range(1945,2021):
                        tahun = 'None'
                except:
                    tahun = 'None'
            else:
                try:
                    tahun = self.extract(nomor+'\s?tahun\s?(.*?)tentang',text50)
                    tahun  = re.findall(r'\d{4}', tahun)
                    if len(tahun)!=0:
                        tahun = tahun[0]
                    else :
                        tahun = nomor[-4:]
                        try:
                            if int(tahun) not in range(1945,2021):
                                tahun = 'None'
                        except:
                            tahun = 'None'
                except:
                    tahun = 'None'
        else:
            nomor = tahun = 'None'

        if tahun=='None':
            try:
                tahun = re.findall(nomor+'\s?tahun\s?(\d{4})',text50)
                if len(tahun)!=0:
                    tahun = tahun[0]
                else :
                    tahun = nomor[-4:]
                    try:
                        if int(tahun) not in range(1945,2021):
                            tahun = 'None'
                    except:
                        tahun = 'None'  
            except:
                tahun = 'None'
        if tahun=='None':
            tahun = re.findall('tahun\s?(\d{4})',text50)
            if len(tahun)!=0:
                tahun = tahun[0]
            else :
                tahun = nomor[-4:]
                try:
                    if int(tahun) not in range(1945,2021):
                        tahun = 'None'
                except:
                    tahun = 'None'
        if tahun=='None':           
            try:
                tahun = self.extract('tahun\s?(.*?)tentang',text50)
                tahun  = re.findall(r'\d{4}', tahun)
                if len(tahun)!=0:
                    tahun = tahun[0]
                else :
                    tahun = nomor[-4:]
                    try:
                        if int(tahun) not in range(1945,2021):
                            tahun = 'None'
                    except:
                        tahun = 'None'
            except:
                tahun = 'None'                    
                    

        return nomor,tahun
        
        
        

    def get_pasal(self,text):

                   
        pasal = list(set(re.findall(self.PATTERN_PASAL, text)))
        
        pasal = [i for i in pasal if re.search(r'\d',i) or i in ['i','ii','iii','iv','v','vi','vii','penutup']]
        
        return sorted(pasal, key=self.natural_keys)

    def menetapkan1(self,text,nama):
        if 'instruksi' not in nama:
            depan = '|'.join(['(?<!perlu\s)memutuskan\s?\:?'])
            belakang = '|'.join([
                                 'ditetapkan\s*?di','disahkan\s*?di','ditetapkan\s*?:',
                                 'diundangkan\s*?di','dikeluarkan\s?di','diumumkan\s?pada'])

            hasil = re.findall(r'({})(.*?)({})(?![a-z]+)(?!\sdalam)'.format(depan, belakang), text)
            if len(hasil)!=0:
                hasil = hasil[0]
                menetapkan = hasil[1]
                text21 = ' '.join(text.split(hasil[-1])[1:])
                return menetapkan.strip(), text21
             
            depan = '|'.join(['(?<!\sdan\s)menetapkan\s?:?'])
            belakang = '|'.join([
                                 'ditetapkan\s*?di','disahkan\s*?di','ditetapkan\s*?:',
                                 'diundangkan\s*?di','dikeluarkan\s?di','diumumkan\s?pada'])

            hasil = re.findall(r'({})(.*?)({})(?![a-z]+)(?!\sdalam)'.format(depan, belakang), text)
            if len(hasil)!=0:
                hasil = hasil[0]
                menetapkan = hasil[1]
                text21 = ' '.join(text.split(hasil[-1])[1:])
                return menetapkan.strip(), text21                
                
                
                
                
                
                
                
                
        depan = '|'.join(['masing\s*?:','untuk\s*?:','menginstruksikan\s*?:?','kepada\s*?:','memutuskan\s?:?'])
        belakang = '|'.join(['instruksi presiden ini mulai berlaku','instruksi ini berlaku','dikeluarkan\s+?di','ditetapkan\s+?di'])
        hasil = re.findall(r'({})(.*?)({})(?![a-z]+)'.format(depan, belakang), text)
        if len(hasil)!=0:
            text21 = ' '.join(text.split(hasil[0][-1])[1:])
            if hasil[0][-1]=='instruksi presiden ini mulai berlaku':
                
                return hasil[0][1].strip()+ ' instruksi presiden ini mulai berlaku pada tanggal ditetapkan.', text21
        
        
            return hasil[0][1].strip(), text21
        return 'None', text

    def menetapkan2(self,text,nama):
        if 'instruksi' not in nama:
            depan = '|'.join(['(?<!perlu\s)memutuskan\s?\:?','menetapkan\s?:?'])
            belakang = '|'.join(['agar setiap orang','agar supaya setiap',
                                 'djakarta\s?','instruksi ini berlaku'])

            hasil = re.findall(r'({})(.*?)({})(?![a-z]+)'.format(depan, belakang), text)
            if len(hasil)!=0:
                hasil = hasil[0]
                menetapkan = hasil[1]
                text21 = ' '.join(text.split(hasil[-1])[1:])
                return menetapkan.strip(), text21
                
            else:
                hasil = re.findall(r'({})(.*?)(ini mulai berlaku pada tanggal ditetapkan)'.format(depan, belakang), text)
                if len(hasil)!=0:
                    hasil = hasil[0]
                    menetapkan = hasil[1]+'ini mulai berlaku pada tanggal ditetapkan'
                    text21 = ' '.join(text.split(hasil[-1])[1:])
                    return menetapkan.strip()   , text21   

                else:
                    hasil = re.findall(r'({})(.*?)(ini berlaku pada tanggal ditetapkan)'.format(depan, belakang), text)
                    if len(hasil)!=0:
                        hasil = hasil[0]
                        menetapkan = hasil[1]+'ini berlaku pada tanggal ditetapkan'
                        text21 = ' '.join(text.split(hasil[-1])[1:])
                        return menetapkan.strip()   , text21       

                        
            depan = '|'.join(['menetapkan\s?:?'])
            belakang = '|'.join(['agar setiap orang','agar supaya setiap',
                                 'djakarta\s?','instruksi ini berlaku'])

            hasil = re.findall(r'({})(.*?)({})(?![a-z]+)'.format(depan, belakang), text)
            if len(hasil)!=0:
                hasil = hasil[0]
                menetapkan = hasil[1]
                text21 = ' '.join(text.split(hasil[-1])[1:])
                return menetapkan.strip(), text21
                
            else:
                hasil = re.findall(r'({})(.*?)(ini mulai berlaku pada tanggal ditetapkan)'.format(depan, belakang), text)
                if len(hasil)!=0:
                    hasil = hasil[0]
                    menetapkan = hasil[1]+'ini mulai berlaku pada tanggal ditetapkan'
                    text21 = ' '.join(text.split(hasil[-1])[1:])
                    return menetapkan.strip()   , text21   

                else:
                    hasil = re.findall(r'({})(.*?)(ini berlaku pada tanggal ditetapkan)'.format(depan, belakang), text)
                    if len(hasil)!=0:
                        hasil = hasil[0]
                        menetapkan = hasil[1]+'ini berlaku pada tanggal ditetapkan'
                        text21 = ' '.join(text.split(hasil[-1])[1:])
                        return menetapkan.strip()   , text21                    



        depan = '|'.join(['masing\s*?:','untuk\s*?:','menginstruksikan\s*?:?','kepada\s*?:','memutuskan\s?:?'])
        belakang = '|'.join(['instruksi presiden ini mulai berlaku','instruksi ini berlaku','dikeluarkan\s+?di','ditetapkan\s+?di'])
        hasil = re.findall(r'({})(.*?)({})(?![a-z]+)'.format(depan, belakang), text)
        if len(hasil)!=0:
            text21 = ' '.join(text.split(hasil[0][-1])[1:])
            if hasil[0][-1]=='instruksi presiden ini mulai berlaku':
                return hasil[0][1].strip()+ ' instruksi presiden ini mulai berlaku pada tanggal ditetapkan.', text21
        
        
            return hasil[0][1].strip(), text21
        return 'None', text


    
    def get_menetapkan(self,text,nama):
        result, text21 = self.menetapkan1(text,nama)
        if result=='None':
            result,text21 = self.menetapkan2(text,nama)
        return result, text21





    
    def potong_mengingat(self,text):
        text = text.replace(' no. ',' nomor ')
        text = re.sub('\sno\.(\d+)',r' nomor \1',text)
        result = []
        for puu in ['peraturan','keputusan','undang','ketetapan','inpres','instruksi']:
            pattern = r'{}.*?nomor.*?tentang.*?;'.format(puu)
            result.extend( [re.sub(r'[;\.,]','',i.split('(')[0].replace('undang-undang dasar negara republik indonesia tahun 1945','')) for i in re.findall(pattern,text) if re.search(pattern,i)])
        #pasal
        pasal_undang_undang = re.findall(r'pasal.*?undang-undang dasar negara republik indonesia tahun 1945',text)
        # ----------- pemrakarsa ------------
        pemrakarsa = 'None'
        for i in pasal_undang_undang:
            for j in re.findall(r'(pasal\s?\d+)', i):
                if 'pasal 21' in j or 'pasal 20' in j:
                    pemrakarsa = 'dpr'
                    break
                elif 'pasal 5' in j:
                    pemrakarsa = 'presiden'
                    break

        result.extend([re.sub(r'\s+',' ',re.sub(r'pasal (5|20|21|4) ayat \([1-2]\),?','',t)).strip() for t in pasal_undang_undang])
        result = list(set([re.sub(r'(?<!pasal\s)(\d+)\s(undang-undang)',r'\2',i.replace('  ','')).strip() for i in result]))
        try:
            result.remove('undang-undang dasar negara republik indonesia tahun 1945')
        except:
            pass
        if result==[]:
            result = re.findall('pasal .*?;',text)
        return result, pemrakarsa


    def ter(self,text):
        text = text.replace('undang-xndang','undang-undang')
        text = text.replace(' no. ',' nomor ').replace('pasa 50','pasal')
        text = re.sub('\sno\.(\d+)',r' nomor \1',text).replace(' nr ',' nomor ')   
        #get dekrit
        a = re.findall(r'(?<![a-z0-9\)]\s)dekrit.*?\d{4};?',text)
        #penetapan
        b = re.findall(r'(?<![a-z0-9\)]\s)penetapan.*?no\.?m?o?r?\s?\d+ tahun \d{4}',text)
        #ketetapan majelis
        c = re.findall('(?<![a-z0-9\)]\s)ketetapan majelis.*?\d{4}',text)
        #SK
        d = re.findall(r'(?<![a-z0-9\)]\s)(sk.*?)dengan',text)    
        #undang undang didepan, baru pasal > undang-undang dasar 1945 pasal 1 ayat (2) dan pasal 2 ayat (3)
        e = re.findall(r'(?<![a-z0-9\)]\s)undang-undang dasar 1945 pasal .*?[\.\,\;]',text)
        #pasal 113 undang-undang dasar sementara republik indonesia
        f = re.findall(r'(?<![a-z0-9\)]\s)d?a?n?\s?(pasal.*?undang-undang.*?)(?:republik|indonesia|1945|[\.\,\;])', text)
        #undang-undang dasar sementara pasal 89, 131 dan 142.
        g = re.findall(r'(?<![a-z0-9\)]\s)undang-undang dasar sementara pasal.*?(?:republik|indonesia|[\.\;])',text)
        #undang-undang nomor 3 jo nomor 19 tahun 1950 dengan persetujuan dewan perwakilan rakyat.
        h = re.findall(r'(?<![a-z0-9\)]\s)undang-undang no\.?m?o?r?\s?.*?tahun \d{4}',text)
        #tri komando
        j = re.findall(r'(?<![a-z0-9\)]\s)(tri komando.*?)[\.\;]', text)
        #pasal ayat 1 undang-undang dasar:
        k = re.findall(r'(?<![a-z0-9\)]\s)pasal.*?dasar', text)
        #peraturan pemerintah nomor 17 tahun 1947
        l = re.findall(r'peraturan.*?nomor.*?tahun\s?\d{4}', text)
        #pasal-pasal 141 ayat 1 dan 192 ayat 1 konstitusi.
        m = re.findall(r'pasal.*?konstitusi', text)
        n = re.findall(r'(?<![a-z0-9\)]\s)keputusan.*?[\.\,\;]', text)


        for i in [b,c,d,e,f,g,h,j,k,l,m,n]:
            a.extend(i) 

        a = [i.split('perlu')[0].split('sebagaimana')[0].split('dengan')[0].split(':')[0] for i in a]
        return a

    #----- ketentuan penutup---------
    def umur(self,text):
        if re.search(r'\d\s?\([a-z]+\)\s?(tahun|bulan|hari)',text):
            return text
        else:
            return 'None'

    def cabut(self,text):
        if 'dicabut' in text and 'tidak berlaku' in text:
            return text
        else:
            return 'None'

    def tanggal_mode(self,text):
        ditetapkan = 'None'
        diundangkan = 'None'

        tgl = re.findall(r'tanggal\s*?\,?:?\s*?(\d{1,2})\s?(\w+)\s?(\d{4})',text)

        if tgl!=[]:
            try:       
                ditetapkan = '{} {} {}'.format(tgl[0][0],
                                               self.correction(tgl[0][1]),tgl[0][2])
                diundangkan = '{} {} {}'.format(tgl[1][0],self.correction(tgl[1][1]),tgl[1][2])
            except :
                pass
        else:

            tgl = re.findall('(\d+)\s?[\-\s]\s?(\d+)\s?[\-\s]\s?(\d{4})',text)
      
            if len(tgl)!=0:
                try:
                    
                    ditetapkan = pd.Timestamp(day = int(tgl[0][0].replace(' ','').replace('-','')),
                                              month = int(tgl[0][1].replace(' ','').replace('-','')),
                                              year = int(tgl[0][2].replace(' ','').replace('-',''))).strftime('%d %b %Y')

                    diundangkan = pd.Timestamp(day = int(tgl[1][0].replace(' ','').replace('-','')),
                                               month = int(tgl[1][1].replace(' ','').replace('-','')),
                                               year = int(tgl[1][2].replace(' ','').replace('-',''))).strftime('%d %b %Y')         
                except:
                    pass                    
                    
        return ditetapkan,diundangkan

    
    def tanggal_mode1(self, teks):
        """untuk mendapat kan tanggal dengan pattern d b y"""
        pattern = '(\d{1,2})('+'|'.join(self.bulan).lower()+')(\d{4})'
        tgls = re.findall(r'{}'.format(pattern),teks.replace(' ','').replace('-',''))
        if tgls==[]:
            return ['None']

        return [ '{} {} {}'.format(tgl[0],tgl[1],tgl[2]) for tgl in tgls]
    
    def tanggal_mode2(self,text):
        text = ' '.join(text.split()[:100])
        tgls = re.findall(r'(\d{1,2})([a-z!"#$%&\'()*+,-.:;<=>?@\\^_`{|}~]+)(\d{4})',
                            text.replace(' ','').replace('-',''))
        if tgls==[]:
            return [{'result':'None',
                           'status':None}]

        result = []
        for tgl in tgls:
            status=True
            b = self.correction(tgl[1])
            if b=='tahun':
                continue
            status = True
            if b == tgl[1]:
                status=None
            if len(b)>9:
                continue
            result.append({'result':'{} {} {}'.format(tgl[0],b,tgl[2]),
                           'status':status})
        if result == []:
            return [{'result':'None',
                           'status':None}]
        return result


    def get_value_tgl(self,tgl):
        ditetapkan,diundangkan = ('None','None')
        tgl = df['result'].tolist()
        ditetapkan = tgl[0]
        try:
            diundangkan = tgl[1]
        except:
            pass     
        return ditetapkan, diundangkan


    def get_pattern(self,isi):
        a = re.findall(r'(?<![A-Z])(1\.|a\.|1\))',isi.strip().split()[0])
        if a==[]:
            return
        a = a[0]
        if a =='1.':
            pattern = r'\s\d{1,2}\.'
        elif a =='a.':
            pattern = r'\s[a-z]{1,2}\.'
        elif a=='1)':
            pattern = r'\s\d{1,2}\)'
        return zip(re.findall(pattern,' '+isi),[i for i in re.split(pattern," "+isi) if i.strip()!=''])  

    def rombak_ketentuan_umum(self,adict):

        result=[]
        for x in adict:
            if x.get('judul_bab') and x.get('judul_bab')=='ketentuan umum':
                isik = x['isi']      
                isi1 = isik.split(':')
                if len(isi1)!=1: 
                   
                    all_isi = ':'.join(isi1[1:])
                    try:
                        pattern = self.get_pattern(all_isi)
                        if pattern:
                            pasal = x.get('pasal')
                            ayat = x.get('ayat')
                            for pentol, value in pattern:
                                data = x.copy()
                                id_ = data.get('id')
                                
                                data.update({'ke':pentol,'isi':pentol+value,'full_text':isik})
                                data.update({'id':'{}_{}_{}_{}'.format(id_,pentol, pasal,ayat)})
                                result.append(data)   
                               

                    except Exception as e:
                        result.append(x)
                       
                else:
                    result.append(x)
            else:
                result.append(x)
        return result
