import json
from dotenv import load_dotenv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import logging

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Настройки Chrome
options = Options()
options.binary_location = "/usr/bin/chromium"
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920x1080")

# Используем системный chromedriver
service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

# Функция загрузки JSON
def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)

# Функция входа в Umico Business
def login_to_umico(driver):
    load_dotenv()
    username = os.getenv("UMICO_USERNAME")
    password = os.getenv("UMICO_PASSWORD")

    if not username or not password:
        raise ValueError("Ошибка: логин или пароль не найдены в .env")

    driver.get("https://business.umico.az/sign-in")
    login_input = WebDriverWait(driver, 40).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='İstifadəçi adı daxil edin']"))
    )
    login_input.send_keys(username)

    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Şifrəni daxil edin']")
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)

    try:
        WebDriverWait(driver, 40).until(EC.url_contains("/account/orders"))
        sleep(3)  # Даем странице стабилизироваться
        logging.info("Успешный вход в Umico Business!")
    except:
        logging.error("Ошибка входа!")
        driver.quit()
        raise ValueError("Ошибка входа! Проверь логин и пароль.")

# Функция для закрытия рекламы
def close_ad(driver):
    try:
        baku_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Баку' or text()='Bakı']"))
        )
        baku_option.click()
        logging.info("Город Баку выбран.")
    except:
        logging.info("Окно выбора города не появилось.")

# Функция обработки товаров
def process_product(driver, product_url, edit_url):
    try:
        logging.info(f"Обрабатываем товар: {product_url}")
        driver.get(product_url)
        sleep(2)
        close_ad(driver)

        # Клик по кнопке "Посмотреть цены всех продавцов"
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Посмотреть цены всех продавцов') or contains(text(), 'Bütün satıcıların qiymətlərinə baxmaq')]"))
            )
            button.click()
        except:
            logging.warning("Не удалось найти кнопку просмотра цен.")
            return

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "MPProductOffer"))
        )

        # Анализируем цены продавцов
        product_offers = driver.find_elements(By.CLASS_NAME, "MPProductOffer")
        if not product_offers:
            logging.warning("Нет предложений по этому товару.")
            return

        lowest_price = float('inf')
        lowest_price_merchant = ""
        super_store_price = None

        for offer in product_offers:
            try:
                merchant = offer.find_element(By.CLASS_NAME, "NameMerchant").text.strip()
                price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-new']").text.strip().replace("₼", "").strip()
                
                price_text = offer.find_element(By.XPATH, ".//span[@data-info='item-desc-price-old']").text.strip()
                price = float(price_text.replace("₼", "").strip())

                if not price_text:
                    continue

                price = float(price_text)

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

        # Если цена конкурента ниже, меняем цену
        if super_store_price is not None and lowest_price < super_store_price:
            logging.info("Меняем цену...")
            driver.get(edit_url)
            sleep(5)

            discount_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Скидочная цена' or @placeholder='Endirimli qiymət']"))
            )

            new_price = round(lowest_price - 0.01, 2)
            discount_input.clear()
            discount_input.send_keys(str(new_price))
            logging.info(f"Новая цена: {new_price} ₼")

            save_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Готово'] or span[text()='Hazır']]"))
            )
            sleep(2)
            save_button.click()
            logging.info("Цена обновлена!")
            sleep(10)
    except Exception as e:
        logging.exception(f"Ошибка при обработке товара {product_url}: {e}")

# Основная функция работы с JSON
def process_products_from_json(json_file):
    products = load_json("product.json")
    for product in products:
        process_product(driver, product["product_url"], product["edit_url"])

if __name__ == "__main__":
    try:
        login_to_umico(driver)
        process_products_from_json("product.json")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
    finally:
        driver.quit()
        logging.info("Работа завершена!")