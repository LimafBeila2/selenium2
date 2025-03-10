import json
import threading
import queue
import os
import logging
from time import sleep
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Настройки логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Функция загрузки JSON
def load_json(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Настройки Chrome
def create_driver():
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# Функция входа в Umico Business
def login_to_umico(driver):
    load_dotenv()
    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    driver.get("https://business.umico.az/sign-in")
    login_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)
    
    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    
    try:
        WebDriverWait(driver, 30).until(EC.url_contains("/account/orders"))
        sleep(3)
        logging.info("Успешный вход в Umico Business!")
    except:
        logging.error("Ошибка входа!")
        driver.quit()
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

# Функция закрытия рекламы / выбора города
def close_ad(driver):
    try:
        # Здесь добавляется возможность выбора города "Баку"
        baku_option = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

# Функция сохранения HTML страниц
def save_page_source(driver, page_type="error"):
    try:
        page_source = driver.page_source
        file_name = f"{page_type}_page_source.html"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(page_source)
        logging.info(f"Страница сохранена в {file_name}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении страницы {page_type}: {e}")

# Функция обработки одного товара
def process_product(q):
    driver = create_driver()
    try:
        login_to_umico(driver)

        while not q.empty():
            product = q.get()
            product_url, edit_url = product["product_url"], product["edit_url"]
            logging.info(f"Обрабатываем товар: {product_url}")
            driver.get(product_url)
            sleep(2)
            close_ad(driver)
            
            try:
                button = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"
                    ))
                )
                button.click()
            except:
                logging.warning("Не удалось найти кнопку просмотра цен.")
                continue
            
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductOffer"))
            )
            
            product_offers = driver.find_elements(By.CLASS_NAME, "MPProductOffer")
            if not product_offers:
                logging.warning("Нет предложений по этому товару.")
                continue
            
            lowest_price = float('inf')
            lowest_price_merchant = ""
            super_store_price = None
            
            for offer in product_offers:
                try:
                    merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
                    
                    price_text_old = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']").text.strip() if offer.find_elements(By.XPATH, ".//span[@data-info='item-desc-price-old']") else None
                    price_text_new = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-new']").text.strip() if offer.find_elements(By.XPATH, ".//span[@data-info='item-desc-price-new']") else None
                    
                    # Выбираем минимальную цену, если оба атрибута найдены
                    price_text = None
                    if price_text_old and price_text_new:
                        price_text = min(price_text_old, price_text_new, key=lambda x: float(x.replace("₼", "").replace(" ", "").strip()))  # Убираем пробелы


                    elif price_text_old:
                        price_text = price_text_old
                    elif price_text_new:
                        price_text = price_text_new
                    # Если цена найдена, очищаем и конвертируем её в число
                    if price_text:
                        price_text_cleaned = price_text.replace("₼", "").replace(" ", "").strip()
                        if not price_text_cleaned:
                            continue
                        
                    price = float(price_text_cleaned)
                    if merchant == "Super Store":
                        super_store_price = price
                    if price < lowest_price:
                        lowest_price = price
                        lowest_price_merchant = merchant
                except Exception as e:
                    logging.warning(f"Ошибка при обработке предложения: {e}")
                    continue
            
            logging.info(f"Самая низкая цена: {lowest_price} от {lowest_price_merchant}")
            if super_store_price is not None:
                logging.info(f"Цена от Super Store: {super_store_price}")

            if lowest_price <= 80:
                logging.info(f"Самая низкая цена ({lowest_price}₼) слишком низкая, пропускаем товар.")
                continue
            
            if super_store_price is not None and lowest_price < super_store_price:
                logging.info("Меняем цену...")

                driver.get(edit_url)
                logging.info(f"Открыта страница изменения цены: {edit_url}")
 
                # Логируем текущий URL после загрузки страницы
                logging.info(f"Текущий URL: {driver.current_url}")

                try:
                    discount_checkbox = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Скидка') or contains(text(), 'Endirim')]//preceding-sibling::div[contains(@class, 'tw-border-')]"))
                    )

                    if 'tw-border-umico-brand-main-brand' not in discount_checkbox.get_attribute('class'):
                        discount_checkbox.click()
                        logging.info("Галочка на скидку поставлена.")

                    discount_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"))
                    )

                    discount_input.clear()
                    discount_input.send_keys(str(round(lowest_price - 0.03, 2)))
                    logging.info(f"Установлена скидочная цена: {round(lowest_price - 0.03, 2)} ₼")

                    save_button = WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово'] or span[text()='Hazır']]"))
                    )

                    save_button.click()
                    logging.info("Цена обновлена!")

                    # Сохраняем обновленную страницу после изменения
                    save_page_source(driver, "updated")
                except Exception as e:
                    logging.error(f"Ошибка при установке скидочной цены: {e}")
                    
                    # Сохраняем страницу ошибки
                    save_page_source(driver, "error")

            q.task_done()
    except Exception as e:
        logging.exception(f"Ошибка при обработке товара: {e}")
    finally:
        driver.quit()

# Функция для запуска потоков
def process_products_from_json(json_file):
    products = load_json(json_file)
    q = queue.Queue()

    for product in products:
        q.put(product)

    threads = []
    num_threads = min(1, len(products))  # Запускаем не больше 10 потоков

    for _ in range(num_threads):
        thread = threading.Thread(target=process_product, args=(q,))
        threads.append(thread)
        thread.start()

    q.join()

    for thread in threads:
        thread.join()

sleep(2)

if __name__ == "__main__":
    process_products_from_json("product.json")
    logging.info("Работа завершена!")
