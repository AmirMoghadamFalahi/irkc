from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import jalali
import psycopg2
import time
from datetime import datetime
import multiprocessing as mp

user = 'postgres'
password = 'Amir7172'
host = 'localhost'
dbname = 'tse'


def coming_to_destination(driver, path_list, click_icon_id):

    # Opening facebook homepage
    driver.get("http://assistance.emdadkhodro.com/emdad/com/objectj/emdad/jsp/usr/default.home.jsp")

    driver.find_element_by_partial_link_text('ورود به سيستم عمليات').click()

    user = driver.find_element_by_name('j_username')
    password = driver.find_element_by_name('j_password')

    user.send_keys('s10002')
    password.send_keys('123456')
    password.send_keys(Keys.RETURN)

    for path in path_list:
        driver.find_element_by_partial_link_text(path).click()

    driver.find_element_by_id(click_icon_id).click()

    window_after = driver.window_handles[1]
    driver.switch_to.window(window_after)

    driver.find_element_by_xpath("//select[@name='daftarOstaniMorajeId']/option[text()='تهران']").click()
    driver.find_element_by_class_name('filterFindEditCell').find_element_by_tag_name('a').click()

    return driver


def extracting_results(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.find_all(name='table', class_='generalText')[0].tbody
    rows = table.find_all(name='tr')

    return rows


def find_appropriate_row_nums(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.find_all(name='table', class_='generalText')[0].tbody
    rows = table.find_all(name='tr')

    element_id_lst = []
    subscription_lst = []

    for i, row in enumerate(rows):

        try:
            class_name = row['class'][0]
        except:
            continue

        if 'listRow' not in class_name:
            continue

        columns = row.find_all('td')

        element_id = columns[0]['id']
        subscription_num = int(columns[2].text.strip())
        full_name = columns[3].text.strip()

        if not full_name.startswith('-'):
            element_id_lst.append(element_id)
            subscription_lst.append(subscription_num)

    print("subscription list:", subscription_lst)

    return element_id_lst, subscription_lst


def insert_data(rows, path_list, click_icon_id):
    conn = psycopg2.connect(user=user, password=password, host=host, dbname=dbname)
    cursor = conn.cursor()

    for i, row in enumerate(rows):

        try:
            class_name = row['class'][0]
        except:
            continue

        if 'listRow' not in class_name:
            continue

        columns = row.find_all('td')

        chassis_num = columns[1].text.strip()
        subscription_num = int(columns[2].text.strip())
        full_name = columns[3].text.strip()
        car_category = columns[4].text.strip()
        service_level = columns[5].text.strip()
        exp_jdate = columns[6].text.strip()
        exp_gdate = jalali.Persian(exp_jdate).gregorian_datetime()
        city = columns[7].text.strip()
        province = columns[8].text.strip()

        try:
            cursor.execute('insert into irankhodro(chassis_num, subscription_num, full_name, car_category, '
                           'service_level, exp_jdate, exp_gdate, city, province, extract_datetime, bank, row_num) '
                           'values (%s,%s,%s,%s,%s,%s,%s,%s,%s, current_timestamp, %s, %s)',
                           (chassis_num, subscription_num, full_name, car_category, service_level, exp_jdate,
                            exp_gdate, city, province, path_list[-1], click_icon_id))
            conn.commit()
        except Exception as e:
            if "duplicate key value violates unique constraint" in str(e):
                conn.rollback()
                continue
            else:
                print(e)
                conn.rollback()

    conn.close()


def next_page(driver):
    footer = driver.find_element_by_class_name('filterFindCell')
    try:
        footer.find_element_by_class_name('generalText').find_element_by_xpath("//td/a/img[@title='صفحه بعد']").click()
        state = True
    except:
        state = False

    return state, driver


def jump_to_page(driver, page_num='3'):

    driver.find_element_by_id('pageInput').clear()
    driver.find_element_by_id('pageInput').send_keys(page_num)
    driver.find_element_by_id('pageInput').send_keys(Keys.RETURN)

    return driver


def register_list(driver, element_id_lst, subscription_lst):

    for i, element_id in enumerate(element_id_lst[::-1]):
        driver.find_element_by_id(element_id).find_element_by_tag_name('input').click()
        lst = driver.find_elements_by_class_name('emdadButton')
        for item in lst:
            if item.get_attribute('value') == "انتخاب اشتراک های علامت دار":
                item.click()

        window_after = driver.window_handles[2]
        driver.switch_to.window(window_after)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        print(subscription_lst[-(i + 1)], 'registered')

        file_ = open(str(datetime.now().year) + '_' + str(datetime.now().month) + '_' + str(datetime.now().day) + '_' +
                     str(subscription_lst[-(i + 1)]) + '.txt', 'w', encoding="utf-8")
        file_.write(str(soup))
        file_.close()

        driver.close()
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)

    return driver


def pipeline(path_list, click_icon_id, timeout):

    # Creating a chromedriver instance
    driver = webdriver.Chrome('C:/Users/HP/webdrivers/chromedriver.exe')  # For Chrome
    # driver = webdriver.Firefox(executable_path='C:/Users/HP/webdrivers/geckodriver.exe') # For Firefox
    driver.implicitly_wait(timeout)

    state = True
    try:
        driver = coming_to_destination(driver, path_list, click_icon_id)

        while state is True:

            # rows = extracting_results(driver)
            # insert_data(rows, path_list, click_icon_id)
            element_id_lst, subscription_lst = find_appropriate_row_nums(driver)

            if len(element_id_lst) != 0:
               driver = register_list(driver, element_id_lst, subscription_lst)
            else:
                driver.quit()
                break

            for page_num in ['3', '2', '1']:
                driver = jump_to_page(driver, str(page_num))
                element_id_lst, subscription_lst = find_appropriate_row_nums(driver)

                if len(element_id_lst) != 0:
                    driver = register_list(driver, element_id_lst, subscription_lst)

            state, driver = next_page(driver)

            if state is False:
                driver.quit()

        return 1

    except Exception as e:
        print(e)
        driver.quit()
        if 'element not interactable' in str(e):
            return 0


if __name__ == '__main__':

    DEFAULT_RUNTIME_INTERVAL = 30
    DEFAULT_TIMEOUT = 20
    HIT_TIME_INTERVAL = 2
    HIT_TIME_TIMEOUT = 8

    while True:

        if datetime.now().hour == 8 and datetime.now().minute >= 20:
            runtime_interval = HIT_TIME_INTERVAL
            timeout = HIT_TIME_TIMEOUT
        else:
            runtime_interval = DEFAULT_RUNTIME_INTERVAL
            timeout = DEFAULT_TIMEOUT

        if datetime.now().minute % runtime_interval == 0:

            path_lists = [['وظايف جاري', 'پيگيري اشتراک', 'اشتراک های قابل جذب و تمدید (بانک 2)']]
            for path_list in path_lists:
                click_icon_ids = ['slct1', 'slct4', 'slct2']
                # click_icon_ids = ['slct1']
                for click_icon_id in click_icon_ids:
                    print('starting pipeline for:', path_list[-1], click_icon_id)
                    result = pipeline(path_list, click_icon_id, timeout)
                    print('pipeline completed successfully at:', datetime.now())
                    if result == 0:
                        break

            print('--------------------------------------')
            if datetime.now().second < 30 and runtime_interval == HIT_TIME_INTERVAL:
                time.sleep(30 - datetime.now().second)
            else:
                time.sleep(60 - datetime.now().second)
        else:
            time.sleep(60 - datetime.now().second)
