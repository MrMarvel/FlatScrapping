from unittest import TestCase
from main import get_flats_on_floor
from utils import initSeleniumWebDriver

class Test(TestCase):
    def test_get_flats_on_floor(self):
        driver = initSeleniumWebDriver('chrome')
        flats = get_flats_on_floor(driver, 3)
