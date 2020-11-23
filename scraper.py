from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import time
from bs4 import BeautifulSoup


def make_driver(timeout=20):

    driver = webdriver.Chrome()
    driver.set_page_load_timeout(timeout)
    driver.implicitly_wait(timeout)
    driver.maximize_window()

    return driver


def go_to_destination(driver, timeout, base_url=None, path_list=None):

    if not base_url:
        base_url = "http://assistance.emdadkhodro.com/emdad/com/objectj/emdad/jsp/usr/default.home.jsp"
    if not path_list:
        path_list = ['وظايف جاري', 'پيگيري اشتراک', 'اشتراک های قابل جذب و تمدید (بانک 2)']

    while True:
        try:
            driver.get(base_url)

            driver.find_element_by_partial_link_text('ورود به سيستم عمليات').click()

            user = driver.find_element_by_name('j_username')
            password = driver.find_element_by_name('j_password')

            user.send_keys('s10002')
            password.send_keys('123456')
            password.send_keys(Keys.RETURN)

            for path in path_list:
                driver.find_element_by_partial_link_text(path).click()

            break

        except Exception as e:
            if 'timeout' in str(e):
                driver.quit()
                time.sleep(1)
                driver = make_driver(timeout)

    return driver


def go_to_register_window(driver, hit_time, icon_id='slct1'):

    if hit_time:
        refresh_interval = 5
    else:
        refresh_interval = 30

    refresh_cnt = 0
    state = True
    while state:

        try:
            click_button = driver.find_element_by_xpath("//*[@id='" + icon_id + "']/img")
            driver.execute_script("arguments[0].click();", click_button)
            break

        except Exception as e:
            print(e)
            if "Message: element not visible" in str(e) or 'Unable to locate element' in str(e):

                if 'j_username' in driver.page_source:
                    print('j_username found')

                    user = driver.find_element_by_name('j_username')
                    password = driver.find_element_by_name('j_password')

                    user.send_keys('s10002')
                    password.send_keys('123456')
                    password.send_keys(Keys.RETURN)

                current_sec = datetime.now().second
                waiting_time = refresh_interval * (int(current_sec/refresh_interval) + 1) - current_sec
                time.sleep(waiting_time)
                driver.refresh()
                refresh_cnt += 1

            else:
                time.sleep(5)
                driver.refresh()
                refresh_cnt += 1

        if not hit_time and refresh_cnt >= 5:
            state = False

        if hit_time and refresh_cnt >= 100:
            state = False

    if state:
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)

    return driver, state


def search_city(driver, timeout, new_timeout=20):
    try:
        driver.implicitly_wait(new_timeout)
        driver.find_element_by_xpath("//select[@name='daftarOstaniMorajeId']/option[text()='تهران']").click()
        driver.find_element_by_class_name('filterFindEditCell').find_element_by_tag_name('a').click()
        time.sleep(2)
        driver.implicitly_wait(timeout)
    except Exception as e:
        print('error in ', e)

    return driver


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


def register(driver, element_id_lst, subscription_lst):

    failed_cnt = 0

    for i, element_id in enumerate(element_id_lst[::-1]):
        driver.find_element_by_id(element_id).find_element_by_tag_name('input').click()
        lst = driver.find_elements_by_class_name('emdadButton')
        for item in lst:
            if item.get_attribute('value') == "انتخاب اشتراک های علامت دار":
                item.click()

        window_after = driver.window_handles[2]
        driver.switch_to.window(window_after)
        time.sleep(0.5)

        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            returned_text = soup.find(class_='validation').td.text.strip()

            print(subscription_lst[-(i + 1)], 'registered')
            print(returned_text)

            if returned_text == '0تعداد موارد اضافه شده :':
                failed_cnt += 1

        except:
            failed_cnt += 1

        # file_ = open(str(datetime.now().year) + '_' + str(datetime.now().month) + '_' + str(datetime.now().day) + '_' +
        #              str(subscription_lst[-(i + 1)]) + '.txt', 'w', encoding="utf-8")
        # file_.write(str(soup))
        # file_.close()

        driver.close()
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)

        if failed_cnt >= 3:
            break

    return driver


def next_page(driver):

    footer = driver.find_element_by_class_name('filterFindCell')
    try:
        footer.find_element_by_class_name('generalText').find_element_by_xpath(
            "//td/a/img[@title='صفحه بعد']").click()
        state = True
    except:
        state = False

    return state, driver


def pipeline(hit_time=False, icon_id='slct1', path_list=None):

    if hit_time:
        timeout = 10
    else:
        timeout = 20

    driver = make_driver(timeout)
    driver = go_to_destination(driver, timeout, path_list=path_list)
    time.sleep(1)

    driver, state = go_to_register_window(driver, hit_time, icon_id)
    if state:
        driver = search_city(driver, timeout)
        while state:
            element_id_lst, subscription_lst = find_appropriate_row_nums(driver)

            if len(element_id_lst) != 0:
                driver = register(driver, element_id_lst, subscription_lst)
                state, driver = next_page(driver)

                if state is False:
                    driver.quit()

            else:
                state = False
                driver.quit()

    else:
        driver.quit()


if __name__ == '__main__':

    DEFAULT_RUNTIME_INTERVAL = 30
    HIT_TIME_INTERVAL = 1

    while True:

        if datetime.now().hour == 8 and datetime.now().minute >= 20:
            hit_time = True
            runtime_interval = HIT_TIME_INTERVAL

        else:
            hit_time = False
            runtime_interval = DEFAULT_RUNTIME_INTERVAL

        if datetime.now().minute % runtime_interval == 0:

            path_lists = [['وظايف جاري', 'پيگيري اشتراک', 'اشتراک های قابل جذب و تمدید (بانک 2)']]
            for path_list in path_lists:
                print('starting pipeline for:', path_list[-1])
                try:
                    pipeline(hit_time=hit_time, icon_id='slct1', path_list=path_list)
                    print('pipeline completed successfully at:', datetime.now())
                except Exception as e:
                    print('whole pipeline error')
                    print(e)

            print('--------------------------------------')
            if not hit_time:
                time.sleep(60 - datetime.now().second)

        else:
            time.sleep(60 - datetime.now().second)
