import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep

# Загрузка ссылок из JSON файла
def load_json(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Чтение JSON файла
data = load_json("C:/Users/Famka/OneDrive/Документы/GitHub/selenium2/product.json")  # Укажи свой путь

# Настройки драйвера
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)




# Проходим по всем ссылкам в JSON
for item in data:
    product_url = item["product_url"]
    edit_url = item["edit_url"]

    # Переходим на product_url
    driver.get(product_url)

    # Ожидаем, пока страница не загрузится
    wait = WebDriverWait(driver, 10)

    # Здесь можно добавить шаги для работы с product_url, если нужно
    print(f"Перешли на {product_url}")

    # Переходим на edit_url
    driver.get(edit_url)
    
    # Ожидаем, пока элементы для ввода логина и пароля не будут загружены
    login_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"]')))
    login_input.send_keys("994102136272-5837")  # Ваш логин

    # Вводим пароль
    password_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
    password_input.send_keys("CagaWAn9")  # Ваш пароль

    # Нажимаем на кнопку входа
    login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="button"]')
    ActionChains(driver).move_to_element(login_button).click().perform()

    # Ждем, пока страница не загрузится после входа
    wait.until(EC.url_changes(edit_url))
    print(f"Вошли на страницу редактирования {edit_url}")

# Оставляем браузер открытым на 60 секунд
sleep(60)

# Закрываем браузер по завершению
driver.quit()
