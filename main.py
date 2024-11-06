from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from core.scraper import scrape_data
from core.sql_queries2 import create_tables, check_if_product_already_exists, store_data
from core.logger import log_message

app = FastAPI()

class ItemList(BaseModel):
    ids: List[str]

@app.post("/store/")
async def store(item_list: ItemList):
    
    unique_ids = list(set(item_list.ids))
    
    create_tables()
    
    # new_products = check_if_product_already_exists(unique_ids)
    new_products = unique_ids
    # print(new_products)
    log_message(f'=================='*20, 0)
    if new_products:
        product_list = scrape_data(new_products)
        # save_csv(product_list)
        if product_list:
            store_data(product_list)
            pass
    else:
        log_message(f'INFO: No new products to scrape', 0)
    log_message(f'=================='*20, 0)
    
    return {
        "message":"Success",
        "ids": new_products
        }