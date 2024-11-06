from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import time
from core.logger import log_message

options = Options()
options.add_argument("--headless")
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')

driver = webdriver.Chrome(options=options)

# for captcha
stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
)

wait = WebDriverWait(driver, 10)  # Set a wait time for elements to load


def scrape_data(prod_ids):
    start = time.time()
    product_list = []

    for id in prod_ids:
        product_dict = {}
        try:
            product_dict['ASIN'] = id
            url = f'https://www.amazon.com/dp/{id}'
            driver.get(url)
            
            # Check for Valid ASIN
            try:
                driver.find_element(By.ID, 'productTitle')  # If no title field, then invalid ASIN
            except:
                log_message(f"ERROR: Product with ASIN {id} not found or invalid.", 1)
                continue
            
            try:
                title = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="productTitle"]')))
                product_dict['title'] = title.text
            except Exception as e:
                log_message(f"ERROR: Could not fetch title for ASIN {id}", 1)
                product_dict['title'] = None  # Handle missing title gracefully
            
            # Scrape Descriptin
            try:
                description = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="productDescription"]')))
                product_dict['description'] = description.text
            except Exception as e:
                log_message(f"ERROR: Could not fetch description for ASIN {id}", 1)

            # Scrape Image Links
            image_links = []
            try:
                list_elements = driver.find_elements(By.CLASS_NAME, 'imageThumbnail')
                for li in list_elements:
                    try:
                        img_tag = li.find_element(By.TAG_NAME, 'img')
                        img_src = img_tag.get_attribute('src')
                        image_links.append(img_src)
                    except Exception as img_exception:
                        print(f'Error fetching image from li element for ASIN {id}: {img_exception}')
                product_dict['image_links'] = image_links
            except Exception as e:
                log_message(f"ERROR: Could not fetch image links for ASIN {id}", 1)
                print(f"Error fetching image thumbnails for ASIN {id}: {e}")
                product_dict['image_links'] = []

            # Scrape Table Data
            # table_info = {}
            description_table = {}
            overview_table = {}
            try:
                # Product Description
                table1 = driver.find_element(By.ID, 'productDetails_detailBullets_sections1')
                rows1 = table1.find_elements(By.TAG_NAME, 'tr')
                for row in rows1:
                    try:
                        key = row.find_element(By.TAG_NAME, 'th').text.strip()
                        value = row.find_element(By.TAG_NAME, 'td').text.strip()
                        # table_info[key] = value
                        description_table[key] = value
                    except Exception as row_exception:
                        log_message(f"ERROR: Could not fetch table data for ASIN {id}", 1)
                        print(f"Error processing row in first table for ASIN {id}: {row_exception}")

                # Product Overview
                try:
                    table2 = driver.find_element(By.XPATH, '//*[@id="productOverview_feature_div"]/div/table')
                    rows2 = table2.find_elements(By.TAG_NAME, 'tr')
                    for row in rows2:
                        try:
                            key = row.find_element(By.XPATH, './td[1]').text.strip()
                            value = row.find_element(By.XPATH, './td[2]').text.strip()
                            # table_info[key] = value
                            overview_table[key] = value
                        except Exception as table2_exception:
                            log_message(f"ERROR: Could not fetch table data for ASIN {id}", 1)
                            print(f"Error processing row in second table for ASIN {id}: {table2_exception}")
                except Exception as e:
                    print(f"Error locating second table for ASIN {id}: {e}")
                
                # product_dict['table_info'] = table_info
                product_dict['description_table'] = description_table
                product_dict['overview_table'] = overview_table
            except Exception as e:
                print(f"Error fetching table data for ASIN {id}: {e}")
                product_dict['table_info'] = {}
            
            log_message(f"EXEC: Data scraped for ASIN {id}", 0)
            product_list.append(product_dict)
        except Exception as e:
            log_message(f"ERROR: Could not scrape data for ASIN {id}", 1)
            print(f"Error scraping data for ASIN {id}: {e}")
    end = time.time()
    log_message(f"EXEC: Scraped {len(product_list)} products in {end-start} seconds", 0)
    # print(product_list[0])
    return product_list


def save_csv(product_list):
    with open('products.csv', 'w') as f:
        f.write(','.join(product_list[0].keys()) + '\n')
        for product in product_list:
            # if value is empty, replace with NA
            for key, value in product.items():
                if not value:
                    product[key] = 'NA'
            row = ','.join([f'"{value}"' for value in product.values()])
            f.write(row + '\n')
            
