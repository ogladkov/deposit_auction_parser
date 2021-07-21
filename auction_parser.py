import pandas as pd
from  bs4 import BeautifulSoup
import requests
from warnings import filterwarnings
filterwarnings('ignore')
import datetime as dt
from time import sleep
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


print('Начало работы...')


# ### Краснодар
def parse_minfinkubani_ru():
    print('Скачиваю аукционы МинФина Кубани...')
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
        if dt.datetime.strptime(d, '%d.%m.%Y') >= dt.datetime.today():
            parsed.append([d, ext_url])
            
    s.close()
    parsed = pd.DataFrame(parsed, columns=['date', 'url'])
    
    return parsed


parsed_minfinkubani = parse_minfinkubani_ru()


# ### Банк России
def parse_cbr_ru():
    print('Скачиваю аукционы Банка России...')
    url = 'https://cbr.ru/DKP/DepoParams/'
    df = pd.read_html(url)[0].iloc[:, 0]
    tod = dt.date.today().strftime("%d.%m.%Y")
    df = df[pd.to_datetime(df, format='%d.%m.%Y') >= tod]
    df = pd.DataFrame({'date':df.to_list(), 'url':[url] * len(df)})
    return df

parsed_cbr = parse_cbr_ru()


# ### Moex
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


def moex_parser(kwords):
    print('Скачиваю аукционы Фед. казначейства и ПФР...')
    
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
            action_date = p.text.lower().split('состоится')[0]
            action_date =                f'{action_date.split()[0]}.{month2num(action_date.split()[1])}.{action_date.split()[2]}'
            action_date = dt.datetime.strptime(action_date, '%d.%m.%Y')
            if action_date >= dt.datetime.today():
                parsed.append([dt.datetime.strftime(action_date, '%d.%m.%Y'),
                               full_url
                              ])

    parsed = pd.DataFrame({'date':[x[0] for x in parsed],
                           'url':[x[1] for x in parsed]})
    
    return parsed


words_fedkazna = ['федеральн', 'казначей']
parsed_fedkazna = moex_parser(words_fedkazna)


words_pfr = ['пенсион', 'фонд']
parsed_pfr = moex_parser(words_pfr)


# ###  Комитет финансов СПБ
def com_spb_parser(kwords):
    print('Скачиваю аукционы Комитета Финансов СПБ...')
    
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
            if action_date >= dt.datetime.today():
                    parsed.append([dt.datetime.strftime(action_date, '%d.%m.%Y'),
                                   news_url
                                  ])

    parsed = pd.DataFrame({'date':[x[0] for x in parsed],
                               'url':[x[1] for x in parsed]})
    
    driver.close()

    return parsed


words_comspb = ['провед', 'депозит']
parsed_comspb = com_spb_parser(words_fedkazna)


### Aggregation
print('Совмещаю таблицы...')

df = parsed_cbr.append(parsed_minfinkubani)
df = df.append(parsed_fedkazna)
df = df.append(parsed_pfr)
df = df.append(parsed_comspb)

df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y')
df.sort_values('date')

# ### Writing
print('Файл успешно записан...')
df.to_excel('parsed_deposit_auctions.xlsx')

