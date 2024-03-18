import os
import re
import shutil
from enum import StrEnum

import bs4
import pandas as pd
from bs4 import BeautifulSoup
from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from flat import Flat, parse_flat_from_textcolor, parse_flat_from_text
from utils.selenium_utils import initSeleniumWebDriver
from utils.temp_file import TempFile

HISTORY_FILENAME = 'history_flats.csv.txt'
HISTORY_TEMP_FILENAME = 'history_flats.tmp'


def get_cards_info(root: bs4.Tag) -> list[bs4.Tag]:
    flat_info_cards = root.find_all(attrs={'class': 'imp-tooltip'})
    return flat_info_cards


def get_flat(info_card: bs4.Tag) -> Flat:
    labels = info_card.find_all('h3')
    if len(labels) == 0:
        raise ValueError(f"Не удалось найти название квартиры: {info_card}")
    flat_label = labels[0].text
    text_status = labels[1].text if len(labels) >= 2 else ''

    return parse_flat_from_text(flat_label, text_status)


def get_flats_on_floor(driver: WebDriver, floor_number=7) -> list[Flat]:
    flats = []
    ignore_flat_errors = False
    for try_num in range(1, 3 + 1):
        logger.info(f"Получаем список квартир с {floor_number} этажа" +
                    (f'. Повторная попытка {try_num}' if try_num > 1 else ''))
        if try_num >= 3:
            ignore_flat_errors = True
            logger.warning("Пропускаем квартиры с ошибками")
        try:
            driver.get(f"https://vik.company/planirovka-{floor_number}-etazh/")
            driver.refresh()
            page_source = BeautifulSoup(driver.page_source, features="html.parser")
            info_cards = get_cards_info(page_source)

            for info_card_num, info_card in enumerate(info_cards):
                try:
                    flat = get_flat(info_card)
                    logger.info(f"{flat.label} {flat.status}")
                    flats.append(flat)
                except Exception as e:
                    logger.exception(e)
                    if ignore_flat_errors:
                        logger.warning(f"Ошибка при получении квартиры #{info_card_num + 1}. Пропускаем")
                        continue
                    logger.warning(f"Ошибка при получении квартиры #{info_card_num + 1}")
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


def safe_df_append_to_history(new_df: pd.DataFrame):
    try:
        was_df = pd.read_csv(HISTORY_FILENAME, encoding='utf-8')
        if len(new_df) <= len(was_df):
            logger.warning(f"История не изменилась. Пропускаем сохранение")
            return
        with TempFile(HISTORY_TEMP_FILENAME) as tmp_file:
            new_df.to_csv(tmp_file, index=False, encoding='utf-8')

            new_file_df = pd.read_csv(tmp_file, encoding='utf-8', dtype=str)
            if not new_file_df.equals(new_df.astype(str)):
                raise Exception(f"История изменилась во время сохранения. Отмена сохранения. new_df:\n"
                                f"{new_file_df[~pd.DataFrame(new_file_df == new_df).all(axis=1)].to_string()}")
            new_file_df_p1 = new_file_df[:len(was_df)]
            if not new_file_df_p1.equals(was_df.astype(str)):
                raise Exception(f"Старая часть истории не сохранилась. Отмена сохранения. new_df:\n"
                                f"{new_file_df_p1[~pd.DataFrame(new_file_df_p1 == was_df).all(axis=1)].to_string()}")
            shutil.move(HISTORY_TEMP_FILENAME, HISTORY_FILENAME)
    except Exception as e:
        logger.exception(e)
        logger.warning("Не удалось сохранить историю. Отмена сохранения")
        raise Exception("Ошибка сохранения")


@logger.catch(reraise=True)
def main():
    logger.add('log.txt', format="{time} {level} {message}", level="DEBUG", rotation="1MB")

    driver = initSeleniumWebDriver('Chrome')

    logger.info("Загружаем историю квартир")
    columns = FlatColumns.columns()

    if not os.path.exists(HISTORY_FILENAME):
        logger.warning(f"Файл {os.path.abspath(HISTORY_FILENAME)} не найден. Создаем новый")
        working_history_df = pd.DataFrame(columns=columns)
        working_history_df.to_csv(HISTORY_FILENAME, index=False)
    working_history_df = pd.read_csv(HISTORY_FILENAME)
    working_history_df.columns = columns

    flats_saved: dict[str, Flat] = dict()
    for _, history_flat in working_history_df.iterrows():
        flat_label = str(history_flat[FlatColumns.FLAT])
        flat_status_str = str(history_flat[FlatColumns.STATUS])
        flat_status = Flat.Status(flat_status_str.lower())
        flats_saved[flat_label] = Flat(flat_label, flat_status)
        assert flats_saved[flat_label] == Flat(flat_label, flat_status)
        pass

    for floor_number in range(2, 8 + 1):
        working_history_table: list[list] = list(working_history_df.values.tolist())
        # Список квартир
        flats_fetch = get_flats_on_floor(driver, floor_number=floor_number)
        for flat in flats_fetch:
            flat_was = flats_saved.get(flat.label, None)
            new_row = [pd.Timestamp.now().strftime('%d-%m-%Y %H:%M'), floor_number, flat.label, flat.status]
            if flat_was is None:
                logger.info(f"Новая квартира \"{flat.label}\" {flat.status}")
                working_history_table.append(new_row)
            elif flat_was != flat:
                logger.info(f"Новое состояние квартиры \"{flat.label}\" {flat.status}")
                working_history_table.append(new_row)
                flats_saved[flat.label] = flat
        if len(working_history_df) < len(working_history_table):
            logger.info("Сохраняем изменения")
            working_history_df = pd.DataFrame(working_history_table, columns=columns)
            safe_df_append_to_history(working_history_df)
    pass
    driver.close()
    pass


if __name__ == "__main__":
    main()
