from unittest import TestCase

import pandas as pd

import main
import utils.selenium_utils as selenium_utils


class Test(TestCase):
    def test_get_flats_on_floor(self):
        driver = selenium_utils.initSeleniumWebDriver('chrome')
        flats = main.get_flats_on_floor(driver, 3)

    def test_safe_df_append_to_history(self):
        df = pd.DataFrame(columns=['Время', 'Этаж', 'Квартира', 'Статус'],
                          data=[['2021-08-01 12:00:00', 3, 'А', 'AVAILABLE']])
        df.to_csv(main.HISTORY_FILENAME, index=False, encoding='utf-8')
        new_df = pd.DataFrame(columns=df.columns, data=df.values.tolist() + [['2021-08-01 12:00:00', 3, 'Б', 'SOLD']])
        main.safe_df_append_to_history(new_df)
        got_df = pd.read_csv(main.HISTORY_FILENAME, encoding='utf-8')
        self.assertTrue(got_df.equals(new_df))

    def test_safe_df_append_to_history2(self):
        df = pd.DataFrame(columns=['Время', 'Этаж', 'Квартира', 'Статус'],
                          data=[['2021-08-01 12:00:00', 3, 'А', 'AVAILABLE']])
        df.to_csv(main.HISTORY_FILENAME, index=False, encoding='utf-8')
        new_df = pd.DataFrame(columns=df.columns, data=[df.values.tolist()[0]] + [['2021-08-01 12:00:00', 3, 'Б', 'SOLD']])
        self.assertRaises(Exception, main.safe_df_append_to_history(new_df))

