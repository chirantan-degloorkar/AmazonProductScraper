# AmazonProductScraper
 
Input - List of strings - (ASIN)

1. Scrapes the following data for each Product.
    - Title
    - Image Links
    - Description Tables
    - Information Tables
2. Stores the scraped data in a SQL-Server Database.

### Database Details - 
* Tables - 
    1. products(product_id, asin, title, description)
    2. images(image_id, product_id, image_link)
    3. product_details(id, product_id, {rest of the columns dynamic})
    4. product_overview(id, product_id,{rest of the columns dynamic})


Instructions to run - 
1. Create and activate virtual environment -
    `python -m venv venv` & `source venv/scripts/activate`
2. Run the fastapi server -
    `fastapi run main.py`
3. Database Connection -
    - create a database and 
    - update the database name in *config.json*
4. navigate to the following url to try the api. http://127.0.0.1:8000/docs 
    - ex. input - 
        - ["B09XL6QBM8", "B09PZHVD8H", "B09VX3JR6G", "B0B4FQQ6WY", "B0BLV34K8F", "B09MBG1PBC"]
5. Check the logs. 
