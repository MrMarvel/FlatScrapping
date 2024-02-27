import os
import re
from enum import StrEnum

import pandas as pd
from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from flat import HISTORY_FILENAME, Flat, parse_flat_from_text
from utils import initSeleniumWebDriver


def get_flats_on_floor(driver: WebDriver, floor_number=7) -> list[Flat]:
    flats = []
    ignore_flat_errors = False
    for try_num in range(1, 3+1):
        logger.info(f"Получаем список квартир с {floor_number} этажа" +
                    (f'. Повторная попытка {try_num}' if try_num > 1 else ''))
        if try_num >= 3:
            ignore_flat_errors = True
            logger.warning("Пропускаем квартиры с ошибками")
        try:
            driver.get(f"https://vik.company/planirovka-{floor_number}-etazh/")
            driver.refresh()

            flat_info_html = driver.find_elements(By.CLASS_NAME, 'imp-tooltip')
            flat_labels = [x.find_element(By.TAG_NAME, 'h3').get_attribute('innerHTML') for x in flat_info_html]

            flats_cards_html: list[WebElement] = driver.find_elements(By.TAG_NAME, "polygon")
            for flat_html_num, flat_html in enumerate(flats_cards_html):
                try:
                    title: str = flat_html.get_attribute('data-shape-title')
                    if 'квартира' not in title.lower():
                        continue
                    color_string: str = flat_html.value_of_css_property('fill')
                    label_numbers = re.findall("\\d+", title)
                    flat_rect_html_number = int(label_numbers[0])
                    flat_info_html_number = flat_rect_html_number - 1
                    flat_label = flat_labels[flat_info_html_number]

                    flat = parse_flat_from_text(flat_label, color_string)
                    flats.append(flat)
                    logger.info(f"{flat.label} {flat.status} {color_string}")
                except Exception as e:
                    logger.exception(e)
                    if ignore_flat_errors:
                        logger.warning(f"Ошибка при получении квартиры #{flat_html_num+1}. Пропускаем")
                        continue
                    logger.warning(f"Ошибка при получении квартиры #{flat_html_num+1}")
                    raise Exception("Flat Error")
            return flats
        except Exception as _:
            logger.warning(f"Ошибка при получении квартир с {floor_number} этажа.")
    raise Exception("Не удалось получить список квартир с этажа")


class FlatColumns(StrEnum):
    TIME = 'Время'
    STAGE = 'Этаж'
    FLAT = 'Квартира'
    STATUS = 'Статус'

    def __repr__(self):
        return self.value

    @classmethod
    def columns(cls) -> list[str]:
        return [x.value for x in cls.__members__.values()]

    @property
    def column_index(self):
        return list(FlatColumns.__members__.values()).index(self)


@logger.catch(reraise=True)
def main():
    logger.add('log.txt', format="{time} {level} {message}", level="DEBUG", rotation="1MB")

    driver = initSeleniumWebDriver('Chrome')

    logger.info("Загружаем историю квартир")
    columns = FlatColumns.columns()

    if not os.path.exists(HISTORY_FILENAME):
        logger.warning(f"Файл {os.path.abspath(HISTORY_FILENAME)} не найден. Создаем новый")
        history_flats = pd.DataFrame(columns=columns)
        history_flats.to_csv('history_flats.csv', index=False)
    history_flats = pd.read_csv('history_flats.csv')
    history_flats.columns = columns

    flats_saved: dict[str, Flat] = dict()
    for _, history_flat in history_flats.iterrows():
        flat_label = str(history_flat[FlatColumns.FLAT])
        flat_status_str = str(history_flat[FlatColumns.STATUS])
        flat_status = Flat.Status(flat_status_str)
        flats_saved[flat_label] = Flat(flat_label, flat_status)
        assert flats_saved[flat_label] == Flat(flat_label, flat_status)
        pass

    for floor_number in range(2, 8 + 1):
        table: list[list] = list(history_flats.values.tolist())
        # Список квартир
        flats_fetch = get_flats_on_floor(driver, floor_number=floor_number)
        for flat in flats_fetch:
            flat_was = flats_saved.get(flat.label, None)
            new_row = [pd.Timestamp.now().strftime('%d-%m-%Y %H:%M'), floor_number, flat.label, flat.status]
            if flat_was is None:
                logger.info(f"Новая квартира \"{flat.label}\" {flat.status}")
                table.append(new_row)
            elif flat_was != flat:
                logger.info(f"Новое состояние квартиры \"{flat.label}\" {flat.status}")
                table.append(new_row)
                flats_saved[flat.label] = flat
        if len(history_flats) < len(table):
            logger.info("Сохраняем изменения")
            history_flats = pd.DataFrame(table, columns=columns)
            history_flats.to_csv(HISTORY_FILENAME, index=False)
    pass
    driver.close()
    pass


if __name__ == "__main__":
    main()
