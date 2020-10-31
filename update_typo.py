import pandas as pd
import json, os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import aril2
def update():
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    """kernel ini untuk update list typo yang ada di spreadsheet:
    https://docs.google.com/spreadsheets/d/1wu1YyBwjrCFUvV3Hz5QwMkOchgGnGPeyAbG7ozXFZsY/edit#gid=1487874818

    jika berhasil, akan muncul tabel dibawah. 
    setelah itu, tolong delete data yg ada di spreadsheet yaa karena data typo sudah otomatis terupdate

    INGAT!! nama kolom di spreadsheet harus `From` dan `To`

    """
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    print('get conection to spreadsheet')
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('/hadoop/bigdome1/script/typo_creds.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('typo')
    all_data = []
    for i in sheet.worksheets():
        all_data.extend(sheet.worksheet(i.title).get_all_records())
    df = pd.DataFrame(all_data)[['From','To']]
    a = df.drop_duplicates(['From','To'])
    a = a.dropna()
    a['From'] = a['From'].transform(lambda x: str(x).lower())
    a['To'] = a['To'].transform(lambda x: str(x).lower())
    print(os.path.join(aril2.__dirname__,'tools','list_flashtext.json'))
    with open(os.path.join(aril2.__dirname__,'tools','list_flashtext.json')) as f:
        data = json.load(f)
    ddf = []
    for i in data:
        ddf.append({'To':i, 'From':data[i]})
    ddf = pd.DataFrame(ddf).explode('From')
    ddf = ddf.drop_duplicates(['From','To'])
    ddf['From'] = ddf['From'].transform(lambda x: str(x).lower())
    ddf['To'] = ddf['To'].transform(lambda x: str(x).lower())
    print(ddf.shape)
    df_all = a.append(ddf)
    df_all = df_all.drop_duplicates(['From','To'])
    typo = {}
    for _,i in df_all.groupby('To')['From'].apply(list).to_frame().iterrows():
        typo.update({_:i['From']})
    print(os.path.join(aril2.__dirname__,'tools','list_flashtext.json'))
    with open(os.path.join(aril2.__dirname__,'tools','list_flashtext.json'),'w') as f:
        json.dump(typo,f)

    print('====sucess===')
    print(df_all.shape)
    print(a.tail())