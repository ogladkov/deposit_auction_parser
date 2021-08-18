
# coding: utf-8

# In[101]:


import pandas as pd
from  bs4 import BeautifulSoup
import requests
from warnings import filterwarnings
filterwarnings('ignore')
import datetime as dt
from time import sleep


# In[102]:


tod_14 = dt.datetime.today()  - dt.timedelta(days=1)


# ### Краснодар

# In[103]:


def parse_minfinkubani_ru():
    domain = 'https://minfinkubani.ru'
    url = 'https://minfinkubani.ru/deposit_funds/selection_parameters.php'
    
    s = requests.Session()
    r = s.get(url, verify=False)
    
    soup = BeautifulSoup(r.text)
    parags = soup.find_all('div', {'class': 'item_mews_title'})
    parsed = []

    for p in parags:
        ext_url = domain + p.a.attrs['href']
        ext_content = BeautifulSoup(requests.get(ext_url, verify=False).text)
        d = ext_url.split('=')[2]
        if dt.datetime.strptime(d, '%d.%m.%Y') >= tod_14:
            parsed.append([d, ext_url])
            
    s.close()
    parsed = pd.DataFrame(parsed, columns=['date', 'url'])
    
    return parsed


# In[104]:


parsed_minfinkubani = parse_minfinkubani_ru()
parsed_minfinkubani


# ### Банк России

# In[105]:


def parse_cbr_ru():
    url = 'https://cbr.ru/DKP/DepoParams/'
    df = pd.read_html(url)[0].iloc[:, 0]
    tod = dt.date.today().strftime("%d.%m.%Y")
    df = df[pd.to_datetime(df, format='%d.%m.%Y') >= tod_14]
    df = pd.DataFrame({'date':df.to_list(), 'url':[url] * len(df)})
    return df


# In[106]:


parsed_cbr = parse_cbr_ru()
parsed_cbr


# ### Moex

# In[107]:


def month2num(month):
    month_dict = {
        'января': 1,
        'февраля': 2,
        'марта': 3,
        'апреля': 4,
        'мая':5,
        'июня': 6,
        'июля': 7,
        'августа': 8,
        'сентября': 9,
        'октября': 10,
        'ноября': 11,
        'декабря': 12
    }
    return month_dict[month]


# In[108]:


def moex_parser(kwords):
    domain = 'https://www.moex.com/'
    url = 'https://www.moex.com/ru/news/?ncat=114'
    
    r = requests.get(url).text
    soup = BeautifulSoup(r)
    parags = soup.find_all('a', {'class': 'news-list__link'})
    
    parsed = []

    for p in parags:
        full_url = domain + p.attrs['href']
        text = p.text.lower()

        for w in kwords:
            if w not in text:
                break
        else:
            try:
                action_date = p.text.lower().split('состоится')[0]
                action_date = f'{action_date.split()[0]}.{month2num(action_date.split()[1])}.{action_date.split()[2]}'
                action_date = dt.datetime.strptime(action_date, '%d.%m.%Y')
                if action_date >= tod_14:
                    parsed.append([dt.datetime.strftime(action_date, '%d.%m.%Y'),
                                   full_url
                                  ])
            except KeyError:
                continue

    parsed = pd.DataFrame({'date':[x[0] for x in parsed],
                           'url':[x[1] for x in parsed]})
    
    return parsed


# In[109]:


words_fedkazna = ['федеральн', 'казначей']
parsed_fedkazna = moex_parser(words_fedkazna)
parsed_fedkazna


# In[110]:


words_pfr = ['пенсион', 'фонд']
parsed_pfr = moex_parser(words_pfr)
parsed_pfr


# ###  Комитет финансов СПБ

# In[111]:


from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from time import sleep


# In[112]:


def com_spb_parser(kwords):
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    url = 'https://комфинспб.рф/committees/news/'
    parsed = []
    
    driver.get(url)
    sleep(10)
    html = driver.page_source
    soup = BeautifulSoup(html)
    h3_list = soup.findAll('h3')

    for e in h3_list:
        text = e.text
        url_id = e['data-id']
        news_url = url + url_id

        for k in kwords:
            if k not in text:
                break
        else:
            text, date = text.split(' - ')
            action_date = dt.datetime.strptime(date, '%d.%m.%Y')
            if action_date >= tod_14:
                    parsed.append([dt.datetime.strftime(action_date, '%d.%m.%Y'),
                                   news_url
                                  ])

    parsed = pd.DataFrame({'date':[x[0] for x in parsed],
                               'url':[x[1] for x in parsed]})
    
    driver.close()

    return parsed


# In[113]:


words_comspb = ['провед', 'депозит']
parsed_comspb = com_spb_parser(words_fedkazna)
parsed_comspb


# ### Aggregation

# In[114]:


df = parsed_cbr.append(parsed_minfinkubani)
df = df.append(parsed_fedkazna)
df = df.append(parsed_pfr)
df = df.append(parsed_comspb)


# In[115]:


df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y')
df = df.sort_values('date')
df


# ### Writing

# In[116]:


df.to_excel('parsed_deposit_auctions.xlsx')


# ### Mailing

# In[52]:


from smtplib import SMTP_SSL
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os


# In[53]:


emails_list = []

with open('emails_list.txt', 'r') as elf:
    emails_list = elf.readlines()
emails_list = [e.strip('\n') for e in emails_list]


# In[64]:


def send(address_to):
    '''
    Send generated files by email
    '''
    fname = 'parsed_deposit_auctions.xlsx'

    print('Формируется email...')
    address = "forrncb@yandex.ru"

    # Compose message
    msg = MIMEMultipart()
    msg['From'] = address
    msg['To'] = address_to
    msg['Subject'] = 'Предстоящие аукционы'

    # Add attachment
    attachment = MIMEBase('application', 'octet-stream')
    with open(fname, 'rb') as file:
        attachment.set_payload(file.read())
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition',
                          'attachment',
                          filename=os.path.basename(fname))
    msg.attach(attachment)

    # Send mail
    with open('sendmail_pswd.txt', 'r') as pf:
        pswd = pf.readline()
    
    smtp = SMTP_SSL('smtp.yandex.ru')
    smtp.login(address, pswd)
    smtp.sendmail(address, address_to, msg.as_string())
    smtp.quit()
    print('Отправлено...')


# In[67]:


send(emails_list[0])
    
if df.shape[0]:
    for e in emails_list[1:]:
        send(e)

