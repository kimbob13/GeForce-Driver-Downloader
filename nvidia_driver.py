# Check NVIDIA Driver Update

from selenium import webdriver
import requests
from tqdm import tqdm
import psutil

from time import sleep
import subprocess
import platform
import os

os_name_value = {
    'Windows 10 64bit'  : 57,
    'Windows 7 64bit'   : 19,
    'Linux aarch64'     : 124,
    'Linux 64bit'       : 12,
    'Solarix x86/x64'   : 13,
    'FreeBSD x64'       : 22,
}

NVIDIA_SMI_PATH = "C:/Windows/System32/nvidia-smi.exe"

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

class NVIDIADriverSearch():
    def __init__(self):
        super().__init__()
        URL = "https://www.nvidia.com/Download/Find.aspx?lang=kr"
        client_os_name = self._get_os_name()
        client_os_value = os_name_value[client_os_name]

        self.gpu_name = self._get_gpu_name()
        self.notebook_driver = self._is_notebook_driver()
        self.gpu_series = self._get_gpu_series()

        print('GPU Model:', self.gpu_name, end='')
        if self.notebook_driver:
            print(' (Notebooks)')
        else:
            print()

        self.driver = webdriver.Firefox()
        self.driver.get(URL)

        self._set_product_series_type()
        self._set_product_series()
        self._set_product_family()
        self._set_operating_system(client_os_value)
        if client_os_value == os_name_value['Windows 10 64bit']:
            self._set_windows_driver_type()
        self._set_whql_driver()
        self._click_search()

    def _get_os_name(self):
        os_type, os_ver = platform.platform().split('-')[:2]
        os_arch = platform.architecture()[0]

        if os_type == 'Windows':
            os_name = '{} {} {}'.format(os_type, os_ver, os_arch)
        elif os_type == 'Linux':
            os_name = '{} {}'.format(os_type, os_arch)

        return os_name

    def _get_gpu_name(self):
        nvidia_smi_name = [NVIDIA_SMI_PATH, "--query-gpu=name", "--format=csv,noheader"]
        gpu_name = subprocess.check_output(nvidia_smi_name)[:-2].decode('ascii')
        if gpu_name.startswith('NVIDIA'): # Newer version of NVIDIA driver returns GPU name stared with 'NVIDIA'
            gpu_name = gpu_name.split()[1:] # Remove 'NVIDIA' in the returned name
            if gpu_name[-1].endswith('3GB') or gpu_name[-1].endswith('6GB'): # GTX 1060 3GB and 6GB are classified as same 'GTX 1060'
                gpu_name = gpu_name[:-1]

            gpu_name = ' '.join(gpu_name)

        return gpu_name

    def _is_notebook_driver(self):
        battery = psutil.sensors_battery()
        return battery != None

    def _get_gpu_series(self):
        '''
        Return GPU series name
        ex) GeForce 10 Series, GeForce RTX 20 Series (Notebook)
        '''
        gpu_name_list = self.gpu_name.split()
        _geforce = gpu_name_list[0]
        if len(gpu_name_list) == 2: # ex) GeForce 605, GeForce 845M, GeForce MX350, etc.
            _name = gpu_name_list[1]
        elif len(gpu_name_list) >= 3:
            _class = gpu_name_list[1]
            _name = gpu_name_list[2]

        if len(_name) == 5: # MX100 ~ MX400 Series
            series_name = 'MX{}00'.format(_name[2])
        elif len(_name) == 4:
            if _name.endswith('M'): # Mobile GPU (GTX 960M, GT 650M etc.)
                series_name = '{}00M'.format(_name[0])
            else: # GeForce 10 Series and above
                if int(_name[0]) >= 2: # GeForce RTX 20 Series and above
                    series_name = '{} {}'.format(_class, _name[:2])
                elif self.notebook_driver and _name.startswith('16'): # Notebook 16 series use 'GTX 16' for series name
                    series_name = '{} {}'.format(_class, _name[:2])
                else: # GeForce 10 Series
                    series_name = '{}'.format(_name[:2])
        elif len(_name) == 3: # GeForce 900 Series and below
            series_name = '{}00'.format(_name[0])
            if self.notebook_driver: # There is a notebook variant of GTX 980, which is classified as GeForce 900M Series
                series_name += 'M'                

        notebook_str = ''
        if self.notebook_driver:
            notebook_str = ' (Notebooks)'

        gpu_series = '{} {} Series{}'.format(_geforce, series_name, notebook_str)

        return gpu_series

    def _set_product_series_type(self):
        '''
        Set product series type
        ex) GeForce, TITAN, Quadro, etc
        '''
        _product_series_type = self.driver.find_element_by_id("selProductSeriesType")
        _product_series_type_list = _product_series_type.find_elements_by_tag_name("option")
        for ps_type in _product_series_type_list:
            if ps_type.text in self.gpu_name:
                product_series_type_val = ps_type.get_attribute("value")
                break

        product_series_type = _product_series_type.find_element_by_xpath("//option[@value='" + product_series_type_val + "']")
        product_series_type.click()

    def _set_product_series(self):
        '''
        Set product series
        ex) GeForce 10 Series, GeForce 900 Series, GeForce RTX 20 Series
        '''
        _product_series = self.driver.find_element_by_id("selProductSeries")
        _product_series_list = _product_series.find_elements_by_tag_name('option')
        for p_series in _product_series_list: # p_series = product_series
            if p_series.text == self.gpu_series:
                product_series_val = p_series.get_attribute("value")
                break
                
        product_series = _product_series.find_element_by_xpath("//option[@value='" + product_series_val + "']")
        product_series.click()

    def _set_product_family(self):
        '''
        Set product family
        ex) GeForce RTX 2070 SUPER, GeForce GTX 1060
        '''
        _product_family = self.driver.find_element_by_id("selProductFamily")
        _product_family_list = _product_family.find_elements_by_tag_name('option')
        for p_family in _product_family_list:
            if p_family.text == self.gpu_name:
                product_family_val = p_family.get_attribute("value")
                break

        product_family = _product_family.find_element_by_xpath("//option[@value='" + product_family_val + "']")
        product_family.click()

    def _set_operating_system(self, value):
        '''
        Set operating system type
        ex) Windows 10 64bit
        '''
        _operating_system = self.driver.find_element_by_id("selOperatingSystem")
        operating_system = _operating_system.find_element_by_xpath("//option[@value='" + str(value) + "']")
        operating_system.click()

    def _set_windows_driver_type(self):
        # value 1 for DCH driver
        windows_driver_type = self.driver.find_element_by_xpath("//select[@id='selDownloadTypeDch']/option[@value='1']")
        windows_driver_type.click()

    def _set_whql_driver(self):
        # value 1 for WHQL driver (i.e. Game Ready Driver)
        whql_driver = self.driver.find_element_by_xpath("//select[@id='ddWHQL']/option[@value='1']")
        whql_driver.click()

    def _click_search(self):
        search_button_pos = self.driver.find_element_by_xpath("//table[@width='100%'][@cellspacing='0'][@cellpadding='2'][@align='center']")
        search_button = search_button_pos.find_element_by_tag_name("a")
        search_button.click()
        sleep(3)

    def _download_driver(self, driver_link):
        driver_link.click()
        sleep(1)
        self.driver.find_element_by_xpath("//a[@id='lnkDwnldBtn']").click()
        sleep(1)
        url = self.driver.find_element_by_xpath("//div[@id='mainContent']/table/tbody/tr/td/a").get_attribute("href")
        file_name = os.path.expanduser("~/Downloads/") + url.split('/')[-1]
        
        r = requests.get(url, stream=True)
        total_size = int(r.headers.get('content-length', 0))
        block_size = 1024
        t = tqdm(total=total_size, unit='iB', unit_scale=True)
        with open(file_name, 'wb') as f:
            for data in r.iter_content(block_size):
                t.update(len(data))
                f.write(data)
        t.close()

        if total_size != 0 and t.n != total_size:
            print("ERROR, something went wrong")

        print('Download Complete!')

    def get_most_recent_driver(self, current_version):
        driver_list = self.driver.find_element_by_xpath("//tr[@id='driverList']")
        driver_version = driver_list.find_elements_by_xpath("//td[@class='gridItem']")[1].text
        driver_link = driver_list.find_element_by_xpath("//td[@class='gridItem driverName']/b/a")

        current_list = list(map(int, current_version.split('.')))
        recent_list = list(map(int, driver_version.split('.')))

        if (current_list[0] == recent_list[0]) and (current_list[1] == recent_list[1]):
            print("You're using the latest version!")
        else:
            if (current_list[0] < recent_list[0]) or \
               ((current_list[0] == recent_list[0]) and (current_list[1] < recent_list[1])):
                # Newer version is available
                print('New version is avilable! - ' + driver_version)
                is_download = input('Would you like to download? (Yes / No): ')
                if is_download.lower().startswith('y'):
                    self._download_driver(driver_link)
                else:
                    print('Do not download new version. Bye!')
            else:
                print('Invalid input')

        self.quit()

    def quit(self):
        self.driver.quit()

def _check_valid_input(current_version):
    if (current_version == None) or (len(current_version) == 0):
        return False

    main_ver, sub_ver = current_version.split('.')
    if len(main_ver) != 3 or len(sub_ver) != 2:
        return False

    return True

def get_current_version():
    nvidia_smi_driver = [NVIDIA_SMI_PATH, "--query-gpu=driver_version", "--format=csv,noheader"]
    current_version = subprocess.check_output(nvidia_smi_driver)[:-2].decode('ascii')

    if _check_valid_input(current_version) == False:
        while True:
            print('Unable to get driver version')
            current_version = input('Enter current NVIDIA driver version> ')

            if current_version.lower().startswith('q'):
                exit()
            elif _check_valid_input(current_version):
                break

            print('Enter a valid version number')

    print('Current version is', current_version)

    return current_version

if __name__ == '__main__':
    current_version = get_current_version()

    nvidia_driver = NVIDIADriverSearch()
    nvidia_driver.get_most_recent_driver(current_version)